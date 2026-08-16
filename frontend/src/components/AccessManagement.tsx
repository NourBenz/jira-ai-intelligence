/** Company-admin overview and focused modal workflows for project access. */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Settings2, ShieldCheck, UserPlus, Users } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";

import { apiRequest } from "../api/client";
import type { AccessUser, ProjectAccessSummary, ScrumTeam } from "../api/types";
import { Modal } from "./Modal";
import { ErrorState, LoadingState } from "./States";

const scrumRoles = ["developer", "product_owner", "scrum_master", "qa", "other"];
type AccessWindow = "team" | "members" | "administrators" | null;
type PendingRemoval = { kind: "member" | "administrator"; userId: number; label: string } | null;

export function AccessManagement({ projectKey }: { projectKey: string }) {
  const queryClient = useQueryClient();
  const [activeWindow, setActiveWindow] = useState<AccessWindow>(null);
  const [teamName, setTeamName] = useState("");
  const [selectedTeamId, setSelectedTeamId] = useState("");
  const [selectedUserId, setSelectedUserId] = useState("");
  const [scrumRole, setScrumRole] = useState("developer");
  const [administratorUserId, setAdministratorUserId] = useState("");
  const [pendingRemoval, setPendingRemoval] = useState<PendingRemoval>(null);
  const teams = useQuery({ queryKey: ["access-teams"], queryFn: () => apiRequest<ScrumTeam[]>("/api/admin/access/teams") });
  const users = useQuery({ queryKey: ["access-users"], queryFn: () => apiRequest<AccessUser[]>("/api/admin/access/users") });
  const summary = useQuery({ queryKey: ["project-access", projectKey], queryFn: () => apiRequest<ProjectAccessSummary>(`/api/admin/access/projects/${projectKey}`), enabled: Boolean(projectKey) });

  useEffect(() => {
    if (!selectedTeamId && teams.data?.length) setSelectedTeamId(String(teams.data[0].id));
    if (!selectedUserId && users.data?.length) setSelectedUserId(String(users.data[0].id));
    if (!administratorUserId && users.data?.length) setAdministratorUserId(String(users.data[0].id));
  }, [administratorUserId, selectedTeamId, selectedUserId, teams.data, users.data]);

  useEffect(() => {
    if (summary.data?.owning_team) setSelectedTeamId(String(summary.data.owning_team.id));
  }, [projectKey, summary.data?.owning_team]);

  const refresh = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["access-teams"] }),
      queryClient.invalidateQueries({ queryKey: ["access-users"] }),
      queryClient.invalidateQueries({ queryKey: ["project-access", projectKey] }),
      queryClient.invalidateQueries({ queryKey: ["projects"] }),
    ]);
  };
  const createTeam = useMutation({ mutationFn: () => apiRequest<ScrumTeam>("/api/admin/access/teams", { method: "POST", body: JSON.stringify({ name: teamName }) }), onSuccess: async (team) => { setTeamName(""); setSelectedTeamId(String(team.id)); await refresh(); } });
  const assignProject = useMutation({ mutationFn: () => apiRequest<void>(`/api/admin/access/projects/${projectKey}/team`, { method: "PUT", body: JSON.stringify({ team_id: Number(selectedTeamId) }) }), onSuccess: refresh });
  const assignMember = useMutation({ mutationFn: () => apiRequest<void>(`/api/admin/access/teams/${selectedTeamId}/members`, { method: "POST", body: JSON.stringify({ user_id: Number(selectedUserId), scrum_role: scrumRole }) }), onSuccess: refresh });
  const grantAdministrator = useMutation({ mutationFn: () => apiRequest<void>(`/api/admin/access/projects/${projectKey}/administrators`, { method: "POST", body: JSON.stringify({ user_id: Number(administratorUserId) }) }), onSuccess: refresh });
  const removeMember = useMutation({ mutationFn: (userId: number) => apiRequest<void>(`/api/admin/access/teams/${summary.data?.owning_team?.id}/members/${userId}`, { method: "DELETE" }), onSuccess: refresh });
  const revokeAdministrator = useMutation({ mutationFn: (userId: number) => apiRequest<void>(`/api/admin/access/projects/${projectKey}/administrators/${userId}`, { method: "DELETE" }), onSuccess: refresh });

  const failure = teams.error || users.error || summary.error || createTeam.error || assignProject.error || assignMember.error || grantAdministrator.error || removeMember.error || revokeAdministrator.error;
  if (teams.isLoading || users.isLoading || summary.isLoading) return <LoadingState label="Loading project access" />;

  const activeUsers = users.data?.filter((user) => user.is_active) ?? [];
  const administratorNames = summary.data?.project_administrator_ids.map((userId) => users.data?.find((user) => user.id === userId)?.username ?? `User ${userId}`) ?? [];

  return (
    <section className="access-management">
      <div className="card-heading">
        <div><span className="section-kicker">Company access</span><h2>Team and project permissions</h2><p>Review the current access model, then open only the management window you need.</p></div>
        <span className="data-badge secure"><ShieldCheck size={14} /> Company administrator</span>
      </div>
      {failure && <ErrorState error={failure} />}

      <div className="access-overview-grid">
        <article className="surface-card access-summary-card">
          <span className="icon-tile"><Users size={20} /></span>
          <div><small>Owning Scrum team</small><h3>{summary.data?.owning_team?.name ?? "Not assigned"}</h3><p>{teams.data?.length ?? 0} teams available</p></div>
          <button className="secondary-button" onClick={() => setActiveWindow("team")} type="button"><Settings2 size={15} /> Manage team</button>
        </article>
        <article className="surface-card access-summary-card">
          <span className="icon-tile"><UserPlus size={20} /></span>
          <div><small>Authorized members</small><h3>{summary.data?.team_members.length ?? 0}</h3><p>{summary.data?.team_members.length ? summary.data.team_members.slice(0, 3).map((member) => member.display_name).join(", ") : "No members assigned"}</p></div>
          <button className="secondary-button" onClick={() => setActiveWindow("members")} type="button"><Settings2 size={15} /> Manage members</button>
        </article>
        <article className="surface-card access-summary-card">
          <span className="icon-tile"><ShieldCheck size={20} /></span>
          <div><small>Project administrators</small><h3>{administratorNames.length}</h3><p>{administratorNames.length ? administratorNames.join(", ") : "Company administrators only"}</p></div>
          <button className="secondary-button" onClick={() => setActiveWindow("administrators")} type="button"><Settings2 size={15} /> Manage administrators</button>
        </article>
      </div>

      <Modal open={activeWindow === "team"} onClose={() => setActiveWindow(null)} eyebrow={`Project ${projectKey}`} title="Owning Scrum team" description="Create a Scrum team or assign the team responsible for this project.">
        <div className="modal-form-stack">
          <label><span>Current owning team</span><strong>{summary.data?.owning_team?.name ?? "No team assigned"}</strong></label>
          <label><span>Select an existing team</span><select value={selectedTeamId} onChange={(event) => setSelectedTeamId(event.target.value)}>{teams.data?.map((team) => <option key={team.id} value={team.id}>{team.name}</option>)}</select></label>
          <button className="primary-button" disabled={!selectedTeamId || assignProject.isPending} onClick={() => assignProject.mutate()} type="button">Assign to {projectKey}</button>
          <div className="modal-divider"><span>or create a team</span></div>
          <form onSubmit={(event: FormEvent) => { event.preventDefault(); if (teamName.trim()) createTeam.mutate(); }}>
            <label><span>New team name</span><input aria-label="New team name" value={teamName} onChange={(event) => setTeamName(event.target.value)} placeholder="Example: Payments Team" maxLength={150} /></label>
            <button className="secondary-button" disabled={!teamName.trim() || createTeam.isPending}>Create Scrum team</button>
          </form>
        </div>
      </Modal>

      <Modal open={activeWindow === "members"} onClose={() => setActiveWindow(null)} eyebrow={summary.data?.owning_team?.name ?? `Project ${projectKey}`} title="Team members" description="Add platform users to the owning Scrum team and define their responsibility." size="large">
        <div className="modal-inline-form">
          <label><span>User</span><select value={selectedUserId} onChange={(event) => setSelectedUserId(event.target.value)}>{activeUsers.map((user) => <option key={user.id} value={user.id}>{displayUser(user)}</option>)}</select></label>
          <label><span>Scrum responsibility</span><select value={scrumRole} onChange={(event) => setScrumRole(event.target.value)}>{scrumRoles.map((role) => <option key={role} value={role}>{role.replaceAll("_", " ")}</option>)}</select></label>
          <button className="primary-button" disabled={!selectedTeamId || !selectedUserId || assignMember.isPending} onClick={() => assignMember.mutate()} type="button"><UserPlus size={15} /> Add member</button>
        </div>
        {summary.data?.team_members.length ? <div className="modal-member-list">{summary.data.team_members.map((member) => <article key={member.user_id}><div className="member-avatar">{member.display_name.slice(0, 2).toUpperCase()}</div><div><strong>{member.display_name}</strong><span>{member.scrum_role?.replaceAll("_", " ") ?? "Responsibility not specified"}</span></div><button className="text-button danger" onClick={() => setPendingRemoval({ kind: "member", userId: member.user_id, label: member.display_name })} type="button">Remove access</button></article>)}</div> : <p className="muted-copy">No members are currently assigned.</p>}
      </Modal>

      <Modal open={activeWindow === "administrators"} onClose={() => setActiveWindow(null)} eyebrow={`Project ${projectKey}`} title="Project administrators" description="Choose who can synchronize Jira data and rebuild this project's AI knowledge index." size="large">
        <div className="modal-inline-form admin-form">
          <label><span>Platform user</span><select value={administratorUserId} onChange={(event) => setAdministratorUserId(event.target.value)}>{activeUsers.filter((user) => user.role !== "admin").map((user) => <option key={user.id} value={user.id}>{displayUser(user)}</option>)}</select></label>
          <button className="primary-button" disabled={!administratorUserId || grantAdministrator.isPending} onClick={() => grantAdministrator.mutate()} type="button"><ShieldCheck size={15} /> Grant administration</button>
        </div>
        {administratorNames.length ? <div className="modal-member-list">{summary.data?.project_administrator_ids.map((userId) => { const user = users.data?.find((candidate) => candidate.id === userId); const label = user?.username ?? `User ${userId}`; return <article key={userId}><div className="member-avatar admin">{label.slice(0, 2).toUpperCase()}</div><div><strong>{label}</strong><span>Can synchronize and index {projectKey}</span></div><button className="text-button danger" onClick={() => setPendingRemoval({ kind: "administrator", userId, label })} type="button">Revoke administration</button></article>; })}</div> : <p className="muted-copy">No project-specific administrators are assigned. Company administrators retain access.</p>}
      </Modal>

      <Modal
        open={pendingRemoval !== null}
        onClose={() => setPendingRemoval(null)}
        eyebrow="Confirm access change"
        title={pendingRemoval?.kind === "member" ? "Remove team access?" : "Revoke project administration?"}
        description={pendingRemoval ? `${pendingRemoval.label} will lose the selected permissions for ${projectKey}.` : undefined}
        footer={<><button className="secondary-button" onClick={() => setPendingRemoval(null)} type="button">Cancel</button><button className="danger-button" onClick={() => { if (!pendingRemoval) return; if (pendingRemoval.kind === "member") removeMember.mutate(pendingRemoval.userId); else revokeAdministrator.mutate(pendingRemoval.userId); setPendingRemoval(null); }} type="button">Confirm removal</button></>}
      >
        <div className="confirmation-copy"><ShieldCheck size={20} /><p>This changes access only in Jira AI Intelligence. It does not delete the person's Jira account or modify Jira issues.</p></div>
      </Modal>
    </section>
  );
}

function displayUser(user: AccessUser): string {
  return user.first_name || user.last_name ? `${user.first_name ?? ""} ${user.last_name ?? ""}`.trim() : user.username;
}
