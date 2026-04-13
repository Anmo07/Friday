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
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shadow-[0_0_15px_rgba(59,130,246,0.4)] group-hover:shadow-[0_0_25px_rgba(59,130,246,0.6)] transition-shadow">
            <Shield className="w-4 h-4 text-white" />
          </div>
          <span className="font-bold text-lg tracking-tight text-white">
            Veritas<span className="text-blue-400">AI</span>
          </span>
        </Link>

        <div className="flex items-center gap-1">
          {navItems.map(({ href, label, icon: Icon }) => {
            const isActive = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                className={`px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition-all duration-200 ${
                  isActive
                    ? "bg-blue-500/15 text-blue-400 shadow-[0_0_10px_rgba(59,130,246,0.1)]"
                    : "text-gray-400 hover:text-white hover:bg-white/5"
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
