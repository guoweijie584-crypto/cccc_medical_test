/**
 * Medical Module - 血糖管理模块
 * 
 * 导出所有血糖管理相关组件
 */

export { MedicalTab } from "./MedicalTab";
export { PatientList } from "./PatientList";
export { PatientDetail } from "./PatientDetail";
export { ConsultationPanel } from "./ConsultationPanel";
export { EvolutionReport } from "./EvolutionReport";
export { MemoryDetailPanel } from "./MemoryDetailPanel";
export { MemorySearchBar } from "./MemorySearchBar";
export { MemoryCreateModal } from "./MemoryCreateModal";

// 类型导出
export type { Patient, GlucoseRecord, ConsultationResponse } from "./MedicalTab";
export type { MemoryNodeData } from "./MemoryDetailPanel";
export type { MemorySearchResult } from "./MemorySearchBar";
