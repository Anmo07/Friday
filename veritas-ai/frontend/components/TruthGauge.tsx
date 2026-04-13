import React from "react";

export const TruthGauge = ({ score }: { score: number }) => {
  const percentage = Math.round(score * 100);
  
  let color = "text-red-500";
  let dropShadow = "drop-shadow-[0_0_15px_rgba(239,68,68,0.6)]";
  if (percentage >= 75) {
    color = "text-green-500";
    dropShadow = "drop-shadow-[0_0_15px_rgba(34,197,94,0.6)]";
  } else if (percentage >= 40) {
    color = "text-yellow-500";
    dropShadow = "drop-shadow-[0_0_15px_rgba(234,179,8,0.6)]";
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
        <span className={`text-4xl font-bold ${color}`}>{percentage}%</span>
        <span className="text-xs text-gray-400 font-semibold uppercase tracking-wider mt-1">Truth Score</span>
      </div>
    </div>
  );
};
