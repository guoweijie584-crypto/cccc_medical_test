/**
 * Medical Module - blood glucose management module
 *
 * Exports all medical-related components.
 */

export { MedicalTab } from "./MedicalTab";
export { PatientList } from "./PatientList";
export { PatientDetail } from "./PatientDetail";
export { ConsultationPanel } from "./ConsultationPanel";
export { EvolutionReport } from "./EvolutionReport";
export { MemoryDetailPanel } from "./MemoryDetailPanel";
export { MemorySearchBar } from "./MemorySearchBar";
export { MemoryCreateModal } from "./MemoryCreateModal";
export { TraceReviewPanel } from "./TraceReviewPanel";
export { SystemAdminPanel } from "./SystemAdminPanel";

// Type exports
export type { Patient, GlucoseRecord, ConsultationResponse } from "./MedicalTab";
export type { MemoryNodeData } from "./MemoryDetailPanel";
export type { MemorySearchResult } from "./MemorySearchBar";
