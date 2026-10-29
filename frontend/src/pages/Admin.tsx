import React, { useEffect, useState } from "react";
import { Wrench } from "lucide-react";
import { api } from "../api/client";
import { AppShell } from "../components/AppShell";

interface Room {
  id: number;
  name: string;
  capacity: number;
  equipment: string[];
}

interface DirectoryUser {
  id: number;
  name: string;
  email: string;
  role: string;
}

export const Admin: React.FC = () => {
  const [activeTab, setActiveTab] = useState<"rooms" | "users" | "system">("rooms");
  const [rooms, setRooms] = useState<Room[]>([]);
  const [users, setUsers] = useState<DirectoryUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      api.get<Room[]>("/rooms").catch(() => []),
      api.get<DirectoryUser[]>("/users").catch(() => []),
    ])
      .then(([roomsData, usersData]) => {
        setRooms(roomsData);
        setUsers(usersData);
      })
      .catch((err) => setError(err.message || "Failed to load directory."))
      .finally(() => setLoading(false));
  }, []);

  return (
    <AppShell
      pageTitle="Administration"
      pageSubtitle="Campus facility rooms, user permissions, and MCP tool registry."
    >
      <div className="space-y-6">
        {/* Error */}
        {error && (
          <div className="error-banner mb-4" role="alert">
            {error}
          </div>
        )}

        {/* ── Tabs ────────────────────────────────────────────── */}
        <div className="editorial-tabs">
          <button
            type="button"
            className={`editorial-tab ${activeTab === "rooms" ? "active" : ""}`}
            onClick={() => setActiveTab("rooms")}
          >
            Campus Rooms ({rooms.length})
          </button>
          <button
            type="button"
            className={`editorial-tab ${activeTab === "users" ? "active" : ""}`}
            onClick={() => setActiveTab("users")}
          >
            University Directory ({users.length})
          </button>
          <button
            type="button"
            className={`editorial-tab ${activeTab === "system" ? "active" : ""}`}
            onClick={() => setActiveTab("system")}
          >
            Services &amp; MCP Registry
          </button>
        </div>

        {/* ── Rooms Tab ───────────────────────────────────────── */}
        {activeTab === "rooms" && (
          <div className="editorial-card-raised p-6">
            <div className="flex items-center justify-between pb-3 mb-4 border-b border-rule">
              <div>
                <h3 className="font-serif text-18 text-ink">Campus Facilities</h3>
                <p className="font-sans text-12 text-ink-soft mt-0.5">
                  Capacities and installed hardware for conflict-free scheduling.
                </p>
              </div>
            </div>

            {loading ? (
              <div className="py-10 font-serif italic text-ink-soft text-14 text-center">
                Loading campus rooms…
              </div>
            ) : rooms.length === 0 ? (
              <div className="py-10 font-serif italic text-ink-soft text-14 text-center">
                No rooms configured in system.
              </div>
            ) : (
              <div className="w-full">
                <table className="w-full text-left text-13 border-collapse">
                  <thead>
                    <tr className="border-b border-rule-strong font-sans text-11 uppercase tracking-wider text-ink-soft">
                      <th className="py-3 px-3.5 font-medium">Room Name</th>
                      <th className="py-3 px-3.5 font-medium">Capacity</th>
                      <th className="py-3 px-3.5 font-medium">Installed Equipment</th>
                      <th className="py-3 px-3.5 font-medium">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-rule font-sans">
                    {rooms.map((room) => (
                      <tr key={room.id} className="hover:bg-tint/40 transition-colors">
                        <td className="py-3 px-3.5 font-serif font-medium text-ink text-14">
                          {room.name}
                        </td>
                        <td className="py-3 px-3.5 font-mono text-12">
                          {room.capacity} seats
                        </td>
                        <td className="py-3 px-3.5">
                          <div className="flex flex-wrap gap-1">
                            {room.equipment && room.equipment.length > 0 ? (
                              room.equipment.map((eq, i) => (
                                <span
                                  key={i}
                                  className="editorial-tag editorial-tag-default text-9 px-1.5 py-0.5"
                                >
                                  {eq}
                                </span>
                              ))
                            ) : (
                              <span className="text-ink-faint text-12">—</span>
                            )}
                          </div>
                        </td>
                        <td className="py-3 px-3.5">
                          <span className="editorial-tag editorial-tag-ok text-9 px-1.5 py-0.5">
                            ACTIVE
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* ── Users Tab ───────────────────────────────────────── */}
        {activeTab === "users" && (
          <div className="editorial-card-raised p-6">
            <div className="flex items-center justify-between pb-3 mb-4 border-b border-rule">
              <div>
                <h3 className="font-serif text-18 text-ink">University Members Directory</h3>
                <p className="font-sans text-12 text-ink-soft mt-0.5">
                  Roster of recognized accounts with role-based scheduling and approval authority.
                </p>
              </div>
            </div>

            {loading ? (
              <div className="py-10 font-serif italic text-ink-soft text-14 text-center">
                Loading member directory…
              </div>
            ) : users.length === 0 ? (
              <div className="py-10 font-serif italic text-ink-soft text-14 text-center">
                No users found.
              </div>
            ) : (
              <div className="w-full">
                <table className="w-full text-left text-13 border-collapse">
                  <thead>
                    <tr className="border-b border-rule-strong font-sans text-11 uppercase tracking-wider text-ink-soft">
                      <th className="py-3 px-3.5 font-medium">Member</th>
                      <th className="py-3 px-3.5 font-medium">Email</th>
                      <th className="py-3 px-3.5 font-medium">Role Authority</th>
                      <th className="py-3 px-3.5 font-medium">Permissions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-rule font-sans">
                    {users.map((u) => (
                      <tr key={u.id} className="hover:bg-tint/40 transition-colors">
                        <td className="py-3 px-3.5 font-serif font-medium text-ink text-14">
                          {u.name}
                        </td>
                        <td className="py-3 px-3.5 font-mono text-12 text-ink-soft">
                          {u.email}
                        </td>
                        <td className="py-3 px-3.5">
                          <span
                            className={`editorial-tag text-9 px-1.5 py-0.5 ${
                              ["chairman", "principal"].includes(u.role)
                                ? "editorial-tag-accent"
                                : u.role === "hod"
                                ? "editorial-tag-warn"
                                : "editorial-tag-default"
                            }`}
                          >
                            {u.role.toUpperCase()}
                          </span>
                        </td>
                        <td className="py-3 px-3.5 text-12 text-ink-soft">
                          {u.role === "chairman"
                            ? "Full approval gate & admin"
                            : u.role === "principal" || u.role === "hod"
                            ? "Review, approve minutes, draft agendas"
                            : u.role === "teacher"
                            ? "Coordinate meetings, request slots"
                            : "Attend meetings, complete assigned tasks"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* ── System / MCP Tab ────────────────────────────────── */}
        {activeTab === "system" && (
          <div className="space-y-6">
            <div className="editorial-card-raised p-6 space-y-4">
              <div>
                <h3 className="font-serif text-18 text-ink">Model Context Protocol (MCP) Server</h3>
                <p className="font-sans text-12 text-ink-soft mt-0.5">
                  Exposes typed meeting capabilities to Claude Desktop or external autonomous orchestrators.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
                <div className="p-4 bg-paper border border-rule rounded-sm space-y-2">
                  <div className="flex items-center gap-2">
                    <Wrench size={16} className="text-accent" />
                    <span className="font-mono text-12 font-medium text-ink">
                      calendar.find_slots
                    </span>
                  </div>
                  <p className="font-sans text-12 text-ink-soft leading-relaxed">
                    Computes non-conflicting time slots across attendees with back-to-back scoring.
                  </p>
                  <span className="editorial-tag editorial-tag-ok text-9 px-1.5 py-0.5">READY</span>
                </div>

                <div className="p-4 bg-paper border border-rule rounded-sm space-y-2">
                  <div className="flex items-center gap-2">
                    <Wrench size={16} className="text-accent" />
                    <span className="font-mono text-12 font-medium text-ink">
                      room.book_room
                    </span>
                  </div>
                  <p className="font-sans text-12 text-ink-soft leading-relaxed">
                    Idempotently books campus facilities with equipment matching and capacity checks.
                  </p>
                  <span className="editorial-tag editorial-tag-ok text-9 px-1.5 py-0.5">READY</span>
                </div>

                <div className="p-4 bg-paper border border-rule rounded-sm space-y-2">
                  <div className="flex items-center gap-2">
                    <Wrench size={16} className="text-accent" />
                    <span className="font-mono text-12 font-medium text-ink">
                      minutes.get_minutes
                    </span>
                  </div>
                  <p className="font-sans text-12 text-ink-soft leading-relaxed">
                    Retrieves version-locked minutes with cryptographic SHA-256 integrity hash.
                  </p>
                  <span className="editorial-tag editorial-tag-ok text-9 px-1.5 py-0.5">READY</span>
                </div>

                <div className="p-4 bg-paper border border-rule rounded-sm space-y-2">
                  <div className="flex items-center gap-2">
                    <Wrench size={16} className="text-accent" />
                    <span className="font-mono text-12 font-medium text-ink">
                      actions.list_actions
                    </span>
                  </div>
                  <p className="font-sans text-12 text-ink-soft leading-relaxed">
                    Exposes grounded action items with source timestamps and status filters.
                  </p>
                  <span className="editorial-tag editorial-tag-ok text-9 px-1.5 py-0.5">READY</span>
                </div>
              </div>
            </div>

            <div className="editorial-card-raised p-6 space-y-3">
              <h3 className="font-serif text-18 text-ink">Backend Infrastructure Health</h3>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-1">
                <div className="p-3 bg-paper border border-rule rounded-sm">
                  <span className="text-10 font-sans text-ink-faint block uppercase tracking-wider">API Framework</span>
                  <span className="font-serif font-medium text-ink text-14 mt-0.5 block">FastAPI 0.115</span>
                </div>
                <div className="p-3 bg-paper border border-rule rounded-sm">
                  <span className="text-10 font-sans text-ink-faint block uppercase tracking-wider">Database ORM</span>
                  <span className="font-serif font-medium text-ink text-14 mt-0.5 block">SQLAlchemy 2.0</span>
                </div>
                <div className="p-3 bg-paper border border-rule rounded-sm">
                  <span className="text-10 font-sans text-ink-faint block uppercase tracking-wider">Vector Embeddings</span>
                  <span className="font-serif font-medium text-ink text-14 mt-0.5 block">ChromaDB Local</span>
                </div>
                <div className="p-3 bg-paper border border-rule rounded-sm">
                  <span className="text-10 font-sans text-ink-faint block uppercase tracking-wider">STT Model</span>
                  <span className="font-serif font-medium text-ink text-14 mt-0.5 block">faster-whisper</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
};
