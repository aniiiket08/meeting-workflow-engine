import React from "react";
import { useNavigate } from "react-router-dom";
import { meetingTasksPath } from "./MeetingWorkLinks";

const STAGES = [
  { key: "schedule", label: "Schedule" },
  { key: "agenda",   label: "Agenda"   },
  { key: "meeting",  label: "Meeting"  },
  { key: "minutes",  label: "Minutes"  },
  { key: "actions",  label: "Actions"  },
] as const;

function statusToStage(status: string): number {
  switch (status) {
    case "requested":
    case "slots_proposed":
      return 0; // Schedule active
    case "room_booked":
    case "scheduled":
      return 1; // Agenda active
    case "agenda_drafted":
    case "agenda_approved":
      return 2; // Meeting active
    case "transcript_uploaded":
    case "minutes_drafted":
      return 3; // Minutes active
    case "minutes_approved":
      return 4; // Actions active
    default:
      return 0;
  }
}

interface Props {
  status: string;
  meetingId?: number;
  className?: string;
}

function stagePath(meetingId: number, key: (typeof STAGES)[number]["key"]): string {
  if (key === "agenda" || key === "schedule" || key === "meeting") {
    return `/meetings/${meetingId}/agenda`;
  }
  if (key === "minutes") return `/meetings/${meetingId}/minutes`;
  return meetingTasksPath(meetingId);
}

export const StageTracker: React.FC<Props> = ({ status, meetingId, className = "" }) => {
  const activeIdx = statusToStage(status);
  const navigate = useNavigate();

  return (
    <div
      className={`w-full relative ${className}`}
      aria-label="Meeting stage"
    >
      {/* Background connector line running through marker centers (marker height is 10px, center at 5px) */}
      <div 
        className="absolute top-[5px] left-[10%] right-[10%] h-px bg-rule -z-0 pointer-events-none" 
        aria-hidden="true"
      />

      {/* 5 equal columns with centered content */}
      <div className="grid grid-cols-5 w-full relative z-10" role="list">
        {STAGES.map((stage, idx) => {
          const isDone = idx < activeIdx;
          const isActive = idx === activeIdx;

          return (
            <div key={stage.key} className="flex flex-col items-center justify-start text-center group">
              <button
                type="button"
                className={`stage-marker ${isDone ? "done" : isActive ? "active" : ""} ${
                  meetingId ? "hover:scale-125 transition-transform" : ""
                }`}
                role="listitem"
                aria-label={`${stage.label}: ${isDone ? "done" : isActive ? "current" : "upcoming"}`}
                disabled={!meetingId}
                onClick={(event) => {
                  event.stopPropagation();
                  if (meetingId) navigate(stagePath(meetingId, stage.key));
                }}
                title={meetingId ? `Go to ${stage.label}` : stage.label}
              />
              <span
                className="font-sans text-10 mt-1 tracking-tight text-center select-none block w-full truncate"
                style={{
                  color: isActive
                    ? "var(--accent)"
                    : isDone
                    ? "var(--ink-soft)"
                    : "var(--ink-faint)",
                  fontWeight: isActive ? 600 : 400,
                }}
              >
                {stage.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
