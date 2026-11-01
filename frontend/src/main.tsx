import React, { Suspense, lazy } from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth, User } from "./lib/auth";
import "./index.css";

// Lazy-loaded routes for code splitting and optimized initial bundle size
const ActionTracker = lazy(() => import("./pages/ActionTracker").then(m => ({ default: m.ActionTracker })));
const Admin = lazy(() => import("./pages/Admin").then(m => ({ default: m.Admin })));
const AgendaEditor = lazy(() => import("./pages/AgendaEditor").then(m => ({ default: m.AgendaEditor })));
const Dashboard = lazy(() => import("./pages/Dashboard").then(m => ({ default: m.Dashboard })));
const Evaluations = lazy(() => import("./pages/Evaluations").then(m => ({ default: m.Evaluations })));
const Login = lazy(() => import("./pages/Login").then(m => ({ default: m.Login })));
const MeetingDetails = lazy(() => import("./pages/MeetingDetails").then(m => ({ default: m.MeetingDetails })));
const MeetingsList = lazy(() => import("./pages/MeetingsList").then(m => ({ default: m.MeetingsList })));
const MemoryChat = lazy(() => import("./pages/MemoryChat").then(m => ({ default: m.MemoryChat })));
const MinutesReview = lazy(() => import("./pages/MinutesReview").then(m => ({ default: m.MinutesReview })));
const NewMeeting = lazy(() => import("./pages/NewMeeting").then(m => ({ default: m.NewMeeting })));
const Profile = lazy(() => import("./pages/Profile").then(m => ({ default: m.Profile })));
const Schedule = lazy(() => import("./pages/Schedule").then(m => ({ default: m.Schedule })));
const TraceViewer = lazy(() => import("./pages/TraceViewer").then(m => ({ default: m.TraceViewer })));

const RouteLoadingFallback: React.FC = () => (
  <div
    className="route-loading-indicator"
    role="status"
    aria-label="Loading page"
  />
);

const ProtectedRoute: React.FC<{
  children: React.ReactNode;
  allowedRoles?: User["role"][];
}> = ({ children, allowedRoles }) => {
  const { user, loading } = useAuth();

  if (loading) return <RouteLoadingFallback />;
  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
};

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <AuthProvider>
      <BrowserRouter>
        <Suspense fallback={<RouteLoadingFallback />}>
          <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/meetings"
            element={
              <ProtectedRoute>
                <MeetingsList />
              </ProtectedRoute>
            }
          />
          <Route
            path="/meetings/new"
            element={
              <ProtectedRoute allowedRoles={["chairman", "principal", "hod", "teacher"]}>
                <NewMeeting />
              </ProtectedRoute>
            }
          />
          <Route
            path="/meetings/:id"
            element={
              <ProtectedRoute>
                <MeetingDetails />
              </ProtectedRoute>
            }
          />
          <Route
            path="/meetings/:id/agenda"
            element={
              <ProtectedRoute>
                <AgendaEditor />
              </ProtectedRoute>
            }
          />
          <Route
            path="/meetings/:id/minutes"
            element={
              <ProtectedRoute>
                <MinutesReview />
              </ProtectedRoute>
            }
          />
          <Route
            path="/actions"
            element={
              <ProtectedRoute>
                <ActionTracker />
              </ProtectedRoute>
            }
          />
          <Route
            path="/schedule"
            element={
              <ProtectedRoute allowedRoles={["chairman", "principal", "hod", "teacher"]}>
                <Schedule />
              </ProtectedRoute>
            }
          />
          <Route
            path="/memory"
            element={
              <ProtectedRoute>
                <MemoryChat />
              </ProtectedRoute>
            }
          />
          <Route
            path="/traces"
            element={
              <ProtectedRoute allowedRoles={["chairman", "principal", "hod"]}>
                <TraceViewer />
              </ProtectedRoute>
            }
          />
          <Route
            path="/evaluations"
            element={
              <ProtectedRoute>
                <Evaluations />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin"
            element={
              <ProtectedRoute allowedRoles={["chairman", "principal"]}>
                <Admin />
              </ProtectedRoute>
            }
          />
          <Route
            path="/profile"
            element={
              <ProtectedRoute>
                <Profile />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  </AuthProvider>
</React.StrictMode>
);
