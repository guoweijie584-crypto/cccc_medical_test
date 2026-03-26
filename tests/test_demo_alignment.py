import asyncio
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from api_server import ConsultationRequest, api_create_consultation, load_patients
from src.evolution.demo_service import build_ui_report, run_demo_evaluation


def test_load_patients_has_expected_shape():
    patients = load_patients()
    assert patients
    patient = patients[0]
    assert {"id", "name", "age", "gender", "diabetesType", "glucoseHistory", "medications"} <= set(patient.keys())
    assert isinstance(patient["glucoseHistory"], list)


def test_consultation_payload_matches_frontend_contract():
    async def _run():
        req = ConsultationRequest(
            patient_id="PAT_bjhl2nvy9f",
            query="空腹血糖8.5需要调整用药吗？",
        )
        return await api_create_consultation(req)

    payload = asyncio.run(_run())
    assert {"query", "patientId", "primaryResponse", "expertOpinions", "evaluationScore", "memories"} <= set(payload.keys())
    assert {"pharmacist", "nutritionist", "doctor"} <= set(payload["expertOpinions"].keys())
    assert isinstance(payload["evaluationScore"], float)


def test_small_demo_evaluation_report_builds():
    run_result = run_demo_evaluation(iterations=1, case_limit=1, export=False)
    report = build_ui_report(run_result)
    assert "summary" in report
    assert "iterations" in report
    assert len(report["iterations"]) == 1
    iteration = report["iterations"][0]
    assert {"avgScore", "medicalAccuracy", "safety", "promptChanges", "memoryChanges"} <= set(iteration.keys())
