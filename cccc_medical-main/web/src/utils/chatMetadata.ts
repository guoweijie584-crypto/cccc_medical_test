import type { SelectedPatientBinding } from "../stores/useMedicalStore";

type ChatRef = Record<string, unknown>;

function buildLegacyPatientMetadata(binding: SelectedPatientBinding): string {
  const lines = [
    `[PATIENT_BINDING patient_id=${binding.patientId} patient_name=${binding.patientName || "unknown"}]`,
    "[PATIENT_PROFILE]",
    `name=${binding.patientName || "unknown"}`,
    binding.age ? `age=${binding.age}` : "",
    binding.gender ? `gender=${binding.gender}` : "",
    binding.diabetesType ? `diabetes_type=${binding.diabetesType}` : "",
    binding.diagnosisDate ? `diagnosis_date=${binding.diagnosisDate}` : "",
    Array.isArray(binding.medications) && binding.medications.length > 0
      ? `medications=${binding.medications.join(" | ")}`
      : "",
    Array.isArray(binding.complications) && binding.complications.length > 0
      ? `complications=${binding.complications.join(" | ")}`
      : "",
    Array.isArray(binding.glucoseRecent) && binding.glucoseRecent.length > 0
      ? `glucose_recent=${binding.glucoseRecent
          .map((item) => `${item.type}:${item.value}${item.timestamp ? `@${item.timestamp}` : ""}`)
          .join(" | ")}`
      : "",
    "[/PATIENT_PROFILE]",
  ];
  return lines.filter(Boolean).join("\n");
}

export function buildPatientContextRefs(binding: SelectedPatientBinding | null | undefined): ChatRef[] {
  if (!binding?.patientId) return [];

  return [
    {
      kind: "text",
      title: "medical_context",
      text: buildLegacyPatientMetadata(binding),
      medical_context: {
        patient_id: binding.patientId,
        patient_name: binding.patientName || "unknown",
        profile: {
          name: binding.patientName || "unknown",
          age: binding.age ?? null,
          gender: binding.gender || "",
          diabetes_type: binding.diabetesType || "",
          diagnosis_date: binding.diagnosisDate || "",
          medications: Array.isArray(binding.medications) ? binding.medications.slice(0, 10) : [],
          complications: Array.isArray(binding.complications) ? binding.complications.slice(0, 10) : [],
          glucose_recent: Array.isArray(binding.glucoseRecent) ? binding.glucoseRecent.slice(-5) : [],
        },
      },
    },
  ];
}

export function stripPatientMetadata(text: string): string {
  const raw = String(text || "");
  if (!raw) return "";

  let next = raw.replace(/^\[PATIENT_BINDING[^\n]*\]\s*\n?/m, "");
  next = next.replace(/\[PATIENT_PROFILE\][\s\S]*?\[\/PATIENT_PROFILE\]\s*\n?/m, "");
  return next.trim();
}

export function sanitizePatientMetadataPreview(text: string, maxLength = 100): string {
  const clean = stripPatientMetadata(text);
  if (clean.length <= maxLength) return clean;
  return `${clean.slice(0, maxLength)}...`;
}
