import { lazy, Suspense } from "react";
import { Redirect, Route, Switch, useLocation } from "wouter";

import { useAuth } from "./auth/AuthContext";
import { canAdministerProject } from "./auth/userDisplay";
import { AppShell } from "./components/AppShell";
import { LoadingState } from "./components/States";
import { LoginPage } from "./pages/LoginPage";
import { ProjectProvider, useProject } from "./project/ProjectContext";

const AdminPage = lazy(() => import("./pages/AdminPage").then((module) => ({ default: module.AdminPage })));
const AssistantPage = lazy(() => import("./pages/AssistantPage").then((module) => ({ default: module.AssistantPage })));
const IssuesPage = lazy(() => import("./pages/IssuesPage").then((module) => ({ default: module.IssuesPage })));
const NotFoundPage = lazy(() => import("./pages/NotFoundPage").then((module) => ({ default: module.NotFoundPage })));
const OverviewPage = lazy(() => import("./pages/OverviewPage").then((module) => ({ default: module.OverviewPage })));
const RiskCenterPage = lazy(() => import("./pages/RiskCenterPage").then((module) => ({ default: module.RiskCenterPage })));
const SprintDetailPage = lazy(() => import("./pages/SprintDetailPage").then((module) => ({ default: module.SprintDetailPage })));
const SprintsPage = lazy(() => import("./pages/SprintsPage").then((module) => ({ default: module.SprintsPage })));
const TeamPage = lazy(() => import("./pages/TeamPage").then((module) => ({ default: module.TeamPage })));

export default function App() {
  const [location] = useLocation();
  const { user, loading } = useAuth();

  if (loading) return <main className="boot-screen"><LoadingState label="Opening secure workspace" /></main>;
  if (location === "/login") return user ? <Redirect to="/" /> : <LoginPage />;
  if (!user) return <Redirect to="/login" />;

  return (
    <ProjectProvider>
      <AppShell>
        <Suspense fallback={<LoadingState label="Loading dashboard view" />}>
          <Switch>
            <Route path="/" component={OverviewPage} />
            <Route path="/issues" component={IssuesPage} />
            <Route path="/sprints" component={SprintsPage} />
            <Route path="/sprints/:id" component={SprintDetailPage} />
            <Route path="/risks" component={RiskCenterPage} />
            <Route path="/team" component={TeamPage} />
            <Route path="/assistant" component={AssistantPage} />
            <Route path="/admin"><ProjectAdminRoute /></Route>
            <Route component={NotFoundPage} />
          </Switch>
        </Suspense>
      </AppShell>
    </ProjectProvider>
  );
}

function ProjectAdminRoute() {
  const { user } = useAuth();
  const { projectKey } = useProject();
  return user && canAdministerProject(user, projectKey) ? <AdminPage /> : <Redirect to="/" />;
}
