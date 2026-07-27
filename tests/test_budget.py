import pytest

from qnn_snr.budget import allocate_budget, enumerate_jobs, resource_accounting


@pytest.mark.parametrize("cost_type,mode,expected_terminal_bases", [
    ("global", "finite_shot_conditional", 1),
    ("local", "finite_shot_conditional", 2),
])
def test_enumerate_jobs_counts(cost_type, mode, expected_terminal_bases):
    depth, n_qubits = 3, 4
    jobs = enumerate_jobs(depth, n_qubits, cost_type, mode)
    node_jobs = [j for j in jobs if j.category == "node_jacobian"]
    terminal_jobs = [j for j in jobs if j.category == "terminal_cost"]
    forward_jobs = [j for j in jobs if j.category == "forward_feature"]

    assert len(node_jobs) == 2 * n_qubits * (depth - 1)
    assert len(terminal_jobs) == 2 * n_qubits * expected_terminal_bases
    assert len(forward_jobs) == 0  # conditional mode: forward features are exact, no shots


def test_end_to_end_mode_adds_forward_jobs():
    depth, n_qubits = 4, 4
    jobs = enumerate_jobs(depth, n_qubits, "local", "finite_shot_end_to_end")
    forward_jobs = [j for j in jobs if j.category == "forward_feature"]
    assert len(forward_jobs) == depth - 1


def test_allocate_budget_sums_exactly_and_is_deterministic():
    depth, n_qubits = 3, 4
    jobs = enumerate_jobs(depth, n_qubits, "local", "finite_shot_conditional")
    for B in (10, 250, 999, 2000):
        alloc1 = allocate_budget(B, jobs)
        alloc2 = allocate_budget(B, jobs)
        assert alloc1 == alloc2
        assert sum(alloc1.values()) == B
        assert all(v >= 1 or B < len(jobs) for v in alloc1.values())


def test_allocate_budget_every_job_gets_at_least_floor():
    depth, n_qubits = 2, 4
    jobs = enumerate_jobs(depth, n_qubits, "global", "finite_shot_conditional")
    B = 100
    alloc = allocate_budget(B, jobs)
    base = B // len(jobs)
    assert all(v in (base, base + 1) for v in alloc.values())


def test_resource_accounting_matches_allocation_total():
    depth, n_qubits = 3, 4
    jobs = enumerate_jobs(depth, n_qubits, "local", "finite_shot_end_to_end")
    B = 5000
    alloc = allocate_budget(B, jobs)
    acc = resource_accounting(B, jobs, alloc)
    assert acc.total_allocated_shots == B
    assert acc.unused_remainder_shots == 0
    assert acc.n_circuits == len(jobs)
