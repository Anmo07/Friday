"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Shield, BarChart3, Clock, MessageSquare, Code2 } from "lucide-react";

const navItems = [
  { href: "/", label: "Home", icon: Shield },
  { href: "/dashboard", label: "Intelligence", icon: BarChart3 },
  { href: "/timeline", label: "Timeline", icon: Clock },
  { href: "/feedback", label: "Feedback", icon: MessageSquare },
  { href: "/developers", label: "API", icon: Code2 },
];

export default function Navbar() {
  const pathname = usePathname();

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 glass border-b border-white/5">
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2.5 group">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-500 to-purple-600 flex items-center justify-center shadow-[0_0_15px_rgba(0,234,255,0.4)] group-hover:shadow-[0_0_25px_rgba(0,234,255,0.6)] transition-shadow">
            <Shield className="w-4 h-4 text-white" />
          </div>
          <span className="font-bold font-mono uppercase tracking-wider text-lg text-white">
            Veritas<span className="text-cyan-400 neon-text">AI</span>
          </span>
        </Link>

        <div className="flex items-center gap-1">
          {navItems.map(({ href, label, icon: Icon }) => {
            const isActive = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                className={`px-4 py-2 rounded-lg text-xs font-mono font-bold uppercase tracking-widest flex items-center gap-2 transition-all duration-200 ${
                  isActive
                    ? "bg-cyan-500/15 text-cyan-400 border border-cyan-500/30 shadow-[0_0_15px_rgba(0,234,255,0.15)]"
                    : "text-gray-400 hover:text-cyan-300 hover:bg-white/5 border border-transparent"
                }`}
              >
                <Icon className="w-4 h-4" />
                {label}
              </Link>
            );
          })}
        </div>
      </div>
    </nav>
  );
}
