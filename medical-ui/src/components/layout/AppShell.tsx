import { ReactNode, useEffect } from 'react';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { usePatientStore } from '../../stores/patientStore';

interface AppShellProps {
  children: ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const fetchPatients = usePatientStore((s) => s.fetchPatients);

  useEffect(() => {
    fetchPatients();
  }, [fetchPatients]);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-surface-950">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-auto">{children}</main>
      </div>
    </div>
  );
}
