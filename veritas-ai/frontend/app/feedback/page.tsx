"use client";
import { useState } from "react";
import { MessageSquare, ThumbsUp, ThumbsDown, Send, CheckCircle } from "lucide-react";
import { API_BASE_URL } from "@/services/api";

export default function FeedbackPage() {
  const [query, setQuery] = useState("");
  const [originalScore, setOriginalScore] = useState("");
  const [userFlag, setUserFlag] = useState<"correct" | "incorrect" | "bias_disagreement" | "">("");
  const [correctedScore, setCorrectedScore] = useState("");
  const [comments, setComments] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (!query || !userFlag) return;
    setSubmitting(true);
    try {
      await fetch(`${API_BASE_URL}/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query,
          original_truth_score: parseFloat(originalScore) || 0,
          user_flag: userFlag,
          user_corrected_score: correctedScore ? parseFloat(correctedScore) : null,
          comments,
        }),
      });
      setSubmitted(true);
    } catch (err) {
      console.error("Feedback submission failed:", err);
    }
    setSubmitting(false);
  };

  if (submitted) {
    return (
      <main className="min-h-screen pt-24 pb-12 px-6 max-w-2xl mx-auto flex flex-col items-center justify-center gap-6">
        <div className="w-20 h-20 rounded-full bg-green-500/10 border border-green-500/20 flex items-center justify-center">
          <CheckCircle className="w-10 h-10 text-green-400" />
        </div>
        <h2 className="text-2xl font-bold text-white">Thank you!</h2>
        <p className="text-gray-400 text-center">Your feedback has been recorded and will be used to improve our truth scoring models.</p>
        <button
          onClick={() => { setSubmitted(false); setQuery(""); setOriginalScore(""); setUserFlag(""); setCorrectedScore(""); setComments(""); }}
          className="px-6 py-3 bg-white/5 border border-white/10 rounded-xl text-gray-300 hover:text-white hover:bg-white/10 transition-all"
        >
          Submit Another
        </button>
      </main>
    );
  }

  return (
    <main className="min-h-screen pt-24 pb-12 px-6 max-w-2xl mx-auto">
      <div className="flex flex-col items-center gap-2 mb-10">
        <h1 className="text-3xl font-bold text-white flex items-center gap-3">
          <MessageSquare className="w-7 h-7 text-blue-400" /> Community <span className="gradient-text">Feedback</span>
        </h1>
        <p className="text-gray-500 text-sm">Help improve our AI by flagging incorrect results</p>
      </div>

      <div className="glass rounded-2xl p-8 flex flex-col gap-6">
        {/* Query */}
        <div className="flex flex-col gap-2">
          <label className="text-xs text-gray-500 uppercase tracking-widest font-bold">Original Query</label>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder='e.g. "Is Apple buying Disney?"'
            className="bg-black/30 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-primary/40 placeholder:text-gray-600"
          />
        </div>

        {/* Original Score */}
        <div className="flex flex-col gap-2">
          <label className="text-xs text-gray-500 uppercase tracking-widest font-bold">Original Truth Score (%)</label>
          <input
            type="number"
            min="0"
            max="100"
            value={originalScore}
            onChange={(e) => setOriginalScore(e.target.value)}
            placeholder="e.g. 72"
            className="bg-black/30 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-primary/40 placeholder:text-gray-600 w-32"
          />
        </div>

        {/* User Flag */}
        <div className="flex flex-col gap-2">
          <label className="text-xs text-gray-500 uppercase tracking-widest font-bold">Your Assessment</label>
          <div className="flex gap-3">
            <button
              onClick={() => setUserFlag("correct")}
              className={`flex items-center gap-2 px-5 py-3 rounded-xl border font-medium transition-all ${
                userFlag === "correct"
                  ? "bg-green-500/15 border-green-500/30 text-green-400"
                  : "bg-black/20 border-white/10 text-gray-400 hover:border-white/20"
              }`}
            >
              <ThumbsUp className="w-4 h-4" /> Correct
            </button>
            <button
              onClick={() => setUserFlag("incorrect")}
              className={`flex items-center gap-2 px-5 py-3 rounded-xl border font-medium transition-all ${
                userFlag === "incorrect"
                  ? "bg-red-500/15 border-red-500/30 text-red-400"
                  : "bg-black/20 border-white/10 text-gray-400 hover:border-white/20"
              }`}
            >
              <ThumbsDown className="w-4 h-4" /> Incorrect
            </button>
            <button
              onClick={() => setUserFlag("bias_disagreement")}
              className={`flex items-center gap-2 px-5 py-3 rounded-xl border font-medium transition-all ${
                userFlag === "bias_disagreement"
                  ? "bg-yellow-500/15 border-yellow-500/30 text-yellow-400"
                  : "bg-black/20 border-white/10 text-gray-400 hover:border-white/20"
              }`}
            >
              Bias Issue
            </button>
          </div>
        </div>

        {/* Corrected Score */}
        {userFlag === "incorrect" && (
          <div className="flex flex-col gap-2 animate-fade-up">
            <label className="text-xs text-gray-500 uppercase tracking-widest font-bold">Your Corrected Score (%)</label>
            <input
              type="number"
              min="0"
              max="100"
              value={correctedScore}
              onChange={(e) => setCorrectedScore(e.target.value)}
              placeholder="What should it be?"
              className="bg-black/30 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-primary/40 placeholder:text-gray-600 w-48"
            />
          </div>
        )}

        {/* Comments */}
        <div className="flex flex-col gap-2">
          <label className="text-xs text-gray-500 uppercase tracking-widest font-bold">Additional Context</label>
          <textarea
            value={comments}
            onChange={(e) => setComments(e.target.value)}
            placeholder="Tell us why you think the result was wrong..."
            rows={3}
            className="bg-black/30 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-primary/40 placeholder:text-gray-600 resize-none"
          />
        </div>

        {/* Submit */}
        <button
          onClick={handleSubmit}
          disabled={!query || !userFlag || submitting}
          className="w-full py-4 bg-gradient-to-r from-blue-600 to-purple-600 text-white font-semibold rounded-xl shadow-[0_0_20px_rgba(99,102,241,0.3)] hover:shadow-[0_0_30px_rgba(99,102,241,0.5)] transition-all disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          <Send className="w-5 h-5" /> {submitting ? "Submitting..." : "Submit Feedback"}
        </button>
      </div>
    </main>
  );
}
