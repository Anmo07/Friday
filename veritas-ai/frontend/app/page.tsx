"use client";
import Dashboard from "../components/Dashboard";

export default function Home() {
  return (
    <main className="min-h-screen p-8 w-full max-w-7xl mx-auto flex flex-col items-center justify-start gap-8">
      <div className="flex flex-col items-center gap-2 mb-4">
        <h1 className="text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-primary to-blue-300">
          Veritas AI Intelligence
        </h1>
        <p className="text-gray-400">Production Grade Multi-Agent Verification Matrix</p>
      </div>

      <Dashboard />
    </main>
  );
}
