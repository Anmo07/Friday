"use client";
import Dashboard from "@/components/Dashboard";

export default function DashboardPage() {
  return (
    <main className="min-h-screen pt-24 pb-12 px-6 w-full max-w-7xl mx-auto flex flex-col items-center gap-8">
      <div className="flex flex-col items-center gap-2 mb-4">
        <h1 className="text-3xl font-bold text-white">
          Intelligence <span className="gradient-text">Console</span>
        </h1>
        <p className="text-gray-500 text-sm">Voice-activated multi-agent truth verification</p>
      </div>
      <Dashboard />
    </main>
  );
}
