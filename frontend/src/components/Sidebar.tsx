"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { logout } from "@/lib/api";

const links = [
  { href: "/search",    label: "Search",    icon: "🔍" },
  { href: "/upload",    label: "Upload",    icon: "📤" },
  { href: "/documents", label: "Documents", icon: "📄" },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-56 shrink-0 flex flex-col border-r border-gray-100 bg-white h-screen sticky top-0 px-4 py-6">
      {/* Logo */}
      <div className="mb-8 px-2">
        <span className="text-lg font-semibold tracking-tight text-gray-900">
          Doc<span className="text-blue-600">Retrieval</span>
        </span>
      </div>

      {/* Nav links */}
      <nav className="flex flex-col gap-1 flex-1">
        {links.map((link) => {
          const active = pathname === link.href;
          return (
            <Link
              key={link.href}
              href={link.href}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                active
                  ? "bg-blue-50 text-blue-700"
                  : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
              }`}
            >
              <span>{link.icon}</span>
              {link.label}
            </Link>
          );
        })}
      </nav>

      {/* Logout */}
      <button
        onClick={logout}
        className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium text-gray-500 hover:bg-gray-50 hover:text-gray-700 transition-colors"
      >
        <span>🚪</span>
        Sign out
      </button>
    </aside>
  );
}