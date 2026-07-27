"""
workload_scheduler.py — Greedy orbital workload scheduler

Assigns a mock queue of compute jobs (inference / training) to satellite
pass windows produced by orbital_math.compute_passes().

This is the "traffic control for compute" layer: it turns raw visibility
windows into an actual resource-allocation plan, which is the piece a pure
pass-prediction dashboard is missing.

Scheduling model
-----------------
- INFERENCE jobs are short and latency-sensitive. They need ONE pass whose
  duration covers the job and whose max elevation clears a minimum quality
  bar (elevation is used here as a simple proxy for link quality / slant
  range — higher elevation means a shorter, cleaner path to the ground
  station).
- TRAINING jobs are long-running and latency-insensitive, but need
  cumulative compute time. They are chunked across as many consecutive
  passes (possibly different satellites) as needed to reach their total
  required duration before their deadline.

This is intentionally a simplified, greedy, single-ground-station model.
A production version would run this across a full constellation with
inter-satellite relay so jobs aren't limited to direct-overhead passes —
that's the natural "next" extension once this is working.
"""

import random
import pandas as pd
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional


@dataclass
class Job:
    job_id: str
    name: str
    job_type: str          # 'inference' or 'training'
    duration_min: float    # total compute minutes required
    priority: int          # 1 (highest) - 3 (lowest)
    min_elevation: float   # minimum acceptable max-elevation for a pass
    submitted_time: datetime
    deadline_hours: float  # how far out the scheduler will look for capacity


JOB_NAME_POOL = {
    'inference': [
        "Vision inference batch", "LLM query burst", "Edge sensor fusion",
        "Real-time translation", "Anomaly detection sweep", "Recommendation scoring",
    ],
    'training': [
        "Gradient sync — vision model", "LLM fine-tune checkpoint",
        "Federated aggregation round", "Foundation model pretrain shard",
        "Reinforcement learning rollout", "Embedding index rebuild",
    ],
}


def generate_job_queue(n_jobs: int, now: datetime, seed: Optional[int] = None) -> List[Job]:
    """Generate a mock, reproducible job queue mixing inference and training work."""
    rng = random.Random(seed)
    jobs = []
    for i in range(n_jobs):
        job_type = rng.choices(['inference', 'training'], weights=[0.65, 0.35])[0]
        if job_type == 'inference':
            duration = rng.uniform(0.5, 4.0)    # minutes — fits in one pass
            min_elev = rng.uniform(20, 45)       # needs a decent-quality pass
            deadline = rng.uniform(0.5, 3.0)     # hours — latency sensitive
            priority = rng.choices([1, 2, 3], weights=[0.5, 0.35, 0.15])[0]
        else:
            duration = rng.uniform(20, 90)       # minutes — needs chaining
            min_elev = rng.uniform(10, 25)        # more tolerant of weak passes
            deadline = rng.uniform(4.0, 12.0)     # hours — can wait
            priority = rng.choices([1, 2, 3], weights=[0.2, 0.4, 0.4])[0]

        jobs.append(Job(
            job_id=f"JOB-{i + 1:03d}",
            name=rng.choice(JOB_NAME_POOL[job_type]),
            job_type=job_type,
            duration_min=round(duration, 1),
            priority=priority,
            min_elevation=round(min_elev, 1),
            submitted_time=now + timedelta(minutes=rng.uniform(0, 15)),
            deadline_hours=round(deadline, 1),
        ))

    # Higher priority (lower number) and earlier submission get scheduled first
    jobs.sort(key=lambda j: (j.priority, j.submitted_time))
    return jobs


def schedule_jobs(jobs: List[Job], passes_df: pd.DataFrame) -> pd.DataFrame:
    """
    Greedy scheduler: assigns jobs to pass windows.

    Returns a DataFrame of scheduled segments with columns:
      job_id, job_name, job_type, priority, satellite, start_time, end_time,
      segment_duration_min, max_elevation, chunk_index, status

    status is one of: SCHEDULED (single-segment job fully placed),
    PARTIAL (training job with some but not all required minutes placed),
    UNSCHEDULED (no capacity found before deadline).
    """
    empty_cols = ['job_id', 'job_name', 'job_type', 'priority', 'satellite',
                  'start_time', 'end_time', 'segment_duration_min',
                  'max_elevation', 'chunk_index', 'status']

    if passes_df.empty:
        rows = [{
            'job_id': j.job_id, 'job_name': j.name, 'job_type': j.job_type,
            'priority': j.priority, 'satellite': None, 'start_time': None,
            'end_time': None, 'segment_duration_min': 0, 'max_elevation': None,
            'chunk_index': 0, 'status': 'UNSCHEDULED'
        } for j in jobs]
        return pd.DataFrame(rows, columns=empty_cols)

    passes = passes_df.sort_values('start_time').reset_index(drop=True).to_dict('records')
    remaining_capacity = [p['duration_min'] for p in passes]  # free minutes per pass window
    used_offset_min = [0.0 for _ in passes]  # minutes already consumed from this pass's start

    segments = []

    for job in jobs:
        deadline = job.submitted_time + timedelta(hours=job.deadline_hours)
        remaining_needed = job.duration_min
        chunk_index = 0
        job_scheduled_any = False

        for i, p in enumerate(passes):
            if remaining_needed <= 0:
                break
            if p['start_time'] < job.submitted_time or p['start_time'] > deadline:
                continue
            if p['max_elevation'] < job.min_elevation:
                continue
            if remaining_capacity[i] <= 0:
                continue

            if job.job_type == 'inference':
                # Needs the whole job to fit in a single, uninterrupted pass.
                # Placed after whatever already occupies this pass window.
                if remaining_capacity[i] >= job.duration_min:
                    seg_start = p['start_time'] + timedelta(minutes=used_offset_min[i])
                    seg_end = seg_start + timedelta(minutes=job.duration_min)
                    segments.append({
                        'job_id': job.job_id, 'job_name': job.name, 'job_type': job.job_type,
                        'priority': job.priority, 'satellite': p['name'],
                        'start_time': seg_start, 'end_time': seg_end,
                        'segment_duration_min': job.duration_min,
                        'max_elevation': p['max_elevation'],
                        'chunk_index': 0, 'status': 'SCHEDULED'
                    })
                    used_offset_min[i] += job.duration_min
                    remaining_capacity[i] -= job.duration_min
                    remaining_needed = 0
                    job_scheduled_any = True
            else:
                # Training: consume as much of this pass as needed/available,
                # also placed after whatever already occupies this window.
                take = min(remaining_capacity[i], remaining_needed)
                seg_start = p['start_time'] + timedelta(minutes=used_offset_min[i])
                seg_end = seg_start + timedelta(minutes=take)
                segments.append({
                    'job_id': job.job_id, 'job_name': job.name, 'job_type': job.job_type,
                    'priority': job.priority, 'satellite': p['name'],
                    'start_time': seg_start, 'end_time': seg_end,
                    'segment_duration_min': take,
                    'max_elevation': p['max_elevation'],
                    'chunk_index': chunk_index, 'status': 'SCHEDULED'
                })
                used_offset_min[i] += take
                remaining_capacity[i] -= take
                remaining_needed -= take
                chunk_index += 1
                job_scheduled_any = True

        if not job_scheduled_any:
            segments.append({
                'job_id': job.job_id, 'job_name': job.name, 'job_type': job.job_type,
                'priority': job.priority, 'satellite': None, 'start_time': None,
                'end_time': None, 'segment_duration_min': 0, 'max_elevation': None,
                'chunk_index': 0, 'status': 'UNSCHEDULED'
            })
        elif remaining_needed > 0.01:
            # Training job partially placed — mark the job as PARTIAL by
            # tagging its last segment; downstream summary treats any job
            # with leftover need as partial rather than fully scheduled.
            segments.append({
                'job_id': job.job_id, 'job_name': job.name, 'job_type': job.job_type,
                'priority': job.priority, 'satellite': None, 'start_time': None,
                'end_time': None, 'segment_duration_min': 0, 'max_elevation': None,
                'chunk_index': chunk_index, 'status': 'PARTIAL'
            })

    return pd.DataFrame(segments, columns=empty_cols)


def summarize_schedule(schedule_df: pd.DataFrame, jobs: List[Job]) -> dict:
    """Compute headline metrics for a scheduler run."""
    total_jobs = len(jobs)

    placed_ids = set(schedule_df.loc[schedule_df['status'] == 'SCHEDULED', 'job_id'])
    partial_ids = set(schedule_df.loc[schedule_df['status'] == 'PARTIAL', 'job_id'])
    unscheduled_ids = set(schedule_df.loc[schedule_df['status'] == 'UNSCHEDULED', 'job_id'])
    fully_scheduled_ids = placed_ids - partial_ids - unscheduled_ids

    scheduled_minutes = schedule_df.loc[
        schedule_df['status'] == 'SCHEDULED', 'segment_duration_min'
    ].sum()

    satellites_used = schedule_df['satellite'].dropna().nunique()

    wait_times = []
    for job in jobs:
        job_segs = schedule_df[(schedule_df['job_id'] == job.job_id) &
                                (schedule_df['status'] == 'SCHEDULED')]
        if not job_segs.empty:
            first_start = job_segs['start_time'].min()
            wait_min = (first_start - job.submitted_time).total_seconds() / 60.0
            wait_times.append(max(0.0, wait_min))

    avg_wait = sum(wait_times) / len(wait_times) if wait_times else 0.0

    return {
        'total_jobs': total_jobs,
        'fully_scheduled': len(fully_scheduled_ids),
        'partial': len(partial_ids - fully_scheduled_ids),
        'unscheduled': len(unscheduled_ids),
        'scheduled_minutes': round(float(scheduled_minutes), 1),
        'satellites_used': int(satellites_used),
        'avg_wait_min': round(avg_wait, 1),
    }
