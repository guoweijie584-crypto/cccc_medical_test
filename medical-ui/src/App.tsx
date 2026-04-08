import { Routes, Route, Navigate } from 'react-router-dom';
import { AppShell } from './components/layout/AppShell';
import { ChatPage } from './pages/ChatPage';
import { MemoryPalacePage } from './pages/MemoryPalacePage';
import { EvaluationPage } from './pages/EvaluationPage';
import { ProfilePage } from './pages/ProfilePage';

export default function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<ChatPage />} />
        <Route path="/memory" element={<MemoryPalacePage />} />
        <Route path="/evaluation" element={<EvaluationPage />} />
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppShell>
  );
}
