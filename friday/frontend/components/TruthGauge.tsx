import React from "react";

export const TruthGauge = ({ score }: { score: number }) => {
  const percentage = Math.round(score * 100);
  
  let color = "text-pink-500";
  let dropShadow = "drop-shadow-[0_0_15px_rgba(236,72,153,0.6)]";
  if (percentage >= 75) {
    color = "text-cyan-400";
    dropShadow = "drop-shadow-[0_0_15px_rgba(0,234,255,0.6)]";
  } else if (percentage >= 40) {
    color = "text-purple-400";
    dropShadow = "drop-shadow-[0_0_15px_rgba(168,85,247,0.6)]";
  }

  const radius = 45;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (percentage / 100) * circumference;

  return (
    <div className="flex flex-col items-center justify-center relative w-48 h-48">
      <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
        <circle
          className="text-gray-800"
          strokeWidth="8"
          stroke="currentColor"
          fill="transparent"
          r={radius}
          cx="50"
          cy="50"
        />
        <circle
          className={`transition-all duration-1000 ease-out ${color} ${dropShadow}`}
          strokeWidth="8"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          stroke="currentColor"
          fill="transparent"
          r={radius}
          cx="50"
          cy="50"
        />
      </svg>
      <div className="absolute flex flex-col items-center justify-center">
        <span className={`text-4xl font-mono font-bold ${color}`}>{percentage}%</span>
        <span className="text-[10px] text-gray-500 font-mono font-bold uppercase tracking-widest mt-2">SYS.TRUTH.SCORE</span>
      </div>
    </div>
  );
};
