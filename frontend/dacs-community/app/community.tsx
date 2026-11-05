"use client";
import { useState, useEffect, useCallback, useRef, useMemo } from "react";
import { useMemberAuth, AccountControls, signOutMember } from "./auth";
import { ProfileEditor, OptionQuestion } from "./profile-editor";
import { MemberAvatar } from "./member-avatar";
import { MemberSheet, memberAccent, memberStyle } from "./member-sheet";
import { MemberLanyard, useLanyardSpace } from "./member-lanyard";
import { ApprovalCelebration } from "./approval-celebration";
import { ProfileCrystal } from "./profile-crystal";
import { DecadeTimeline } from "./decade-timeline";
import { auroraSweep, celebrated, markCelebrated } from "./fx";
import { MemberBadges } from "./member-badges";
import { OfficialWebsite, CoreWorkspace, publicWebsite, shareContentUrl, logoApplicationUrl } from "./resources";
import {MeetingHub,MeetingNotifications,useMeetingAccess,useMeetingTools} from "./meeting-hub";
import {NewsBoard} from "./news";
import {LogoReview} from "./logo-review";
import {canReviewLogo,bodyLabel,bodyLevel,canOrganise,meetingBodies,type MeetingSeed} from "@/lib/meetings";
import { GroupDiscussion } from "./discussion";
import { FlagshipOverview } from "./workplan";
import { WorkingGroupPage, type WgTab } from "./wg-page";
import { subscribeWorkplan, linkActivity } from "@/lib/coordination-store";
import type { WorkItem } from "@/lib/coordination";
import { DecisionRegister } from "./decisions";
import { Consultations, useConsultations } from "./consultations";
import { SecretariatDashboard } from "./dashboard";
import { MailingLists, mailingAccess } from "./mailing-lists";
import { RoleRequestsPanel } from "./role-requests";
import { GroupRequests } from "./group-requests";
import { AttachmentList, AttachmentPicker, shareBody } from "./attachments";
import type { Attachment } from "@/lib/files-store";
import { Messages, chatSummary } from "./messages";
import { accentStyle, eventAccent } from "@/lib/event-style";
import { WelcomeVideo } from "./welcome-video";
import { DecadeIntro } from "./decade-intro";
import { TorCard, TorDialog, termsOfReference } from "./terms-of-reference";
import { Templates } from "./templates";
import { ActivityDetail } from "./activity-detail";
import { CreatedBy, PeopleContext } from "./people-context";
import { TaskBoard, TaskBoards, boardBodies } from "./task-board";
import { subscribeMyTasks } from "@/lib/task-store";
import { dueLabel, dueState, isNewFor, localToday, type Task } from "@/lib/tasks";
import { ChatMonitor } from "./chat-monitor";
import { isGroup, isOwnerAccount, isUnread, markRead as markChatRead, otherMember, subscribeMonitors, subscribeMyChats, subscribeReports, type Chat, type ChatReport } from "@/lib/chat-store";
import { syncOwnEntries } from "@/lib/mailing-store";
import { subscribePendingRequests, subscribeOwnRequest, type RoleRequest } from "@/lib/role-requests";
import { applyToGroup, subscribeBodyApplications, subscribeOwnApplications, subscribePendingApplications, type Application } from "@/lib/applications";
import { MembersMap } from "./members-map";
import { MyActions } from "./my-actions";
import { subscribeMyActions, fetchEvent, subscribeMemberStats, publishMemberStats, type MemberStats } from "@/lib/coordination-store";
import type { ActionItem } from "@/lib/coordination";
import { isUnescoSecretariat } from "@/lib/member-roles";
import { subscribeInbox, markRead, type InboxItem } from "@/lib/discussion-store";
import { bodySpace } from "@/lib/body-spaces";
import { documentFolder } from "@/lib/workspace-links";
import { DecadeCalendar } from "./calendar";
import { GoalPicker, GoalLabels } from "./goal-picker";
import { linkedGroups, activityGroups,allGoalIds,isDecadeWide } from "@/lib/decade-goals";
import type { CalendarEvent } from "@/lib/calendar";
import {
  GovernanceDirectory,
  GovernanceSeats,
  SecretariatPanel,
  UnescoMembers,
} from "./governance";
import { blankProfile, optionsFor, emptyBody } from "@/lib/profile-options";
import { subscribeCategories } from "@/lib/store";
import { loadCommunity, saveCommunity, friendlyError } from "@/lib/store";
import { saveTheme, storedTheme } from "@/lib/theme";
import { useCountUp, useScrollFlags } from "@/hooks/use-motion";
import { photos, groupPhotos, type Photo } from "@/lib/imagery";
import { PhotoBackdrop } from "./photo";
import {
  Users,
  Briefcase,
  Layers,
  UserRound,
  Search,
  Plus,
  Sun,
  Moon,
  Globe,
  MapPin,
  Clock,
  Calendar,
  CalendarDays,
  CalendarClock,
  ArrowUpRight,
  ArrowRight,
  ArrowLeft,
  ArrowUp,
  ArrowDown,
  Check,
  Newspaper,
  Bookmark,
  Hourglass,
  Satellite,
  Shield,
  ShieldCheck,
  Leaf,
  Megaphone,
  ChartNoAxesCombined,
  Snowflake,
  Network,
  FileCheck,
  FolderOpen,
  BadgeCheck,
  LayoutDashboard,
  LoaderCircle,
  ListChecks,
  BookMarked,
  LogIn,
  LogOut,
  Mail,
  Menu,
  RefreshCw,
  ChevronDown,
  ChevronRight,
  type LucideIcon,
  MessageCircle,
  ShieldAlert,
  PlayCircle,
  ScrollText,
  Presentation,
  Milestone,
  SquareKanban,
  Rocket,
  UserPlus,
} from "lucide-react";
import { DropdownMenu } from "radix-ui";
import { Sheet, SheetContent, SheetTitle, SheetDescription } from "@/components/ui/sheet";
import {
  Dialog,
  DialogContent,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  Select,
  SelectTrigger,
  SelectContent,
  SelectItem,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "sonner";
import { groups, regions, match } from "@/lib/data";
import { asset } from "@/lib/base";
type View =
  | "Community"
  | "Members"
  | "Opportunities"
  | "Working Groups"
  | "Find expertise"
  | "My contributions"
  | "My profile"
  | "Governance"
  | "UNESCO Secretariat"
  | "Official Decade website"
  | "News"
  | "Meeting polls"
  | "Logo review"
  | "Calendar"
  | "Core Group workspace"
  | "Work plans"
  | "Decision register"
  | "Mailing lists"
  | "Messages"
  | "Chat moderation"
  | "Templates"
  | "Decade timeline"
  | "Task boards"
  | "Dashboard";
type NavItem = { view: View; label: string; title?: string; icon: LucideIcon; description: string; photo: Photo };
// Navigation grouped by purpose. Internal view names are unchanged.
const navGroups: { label: string; items: NavItem[] }[] = [
  { label: "Overview", items: [
    { view: "Community", label: "Home", icon: LayoutDashboard, description: "Updates, open activities and Working Groups from across the Decade.", photo: photos.icebergFjord },
    { view: "News", label: "News", icon: Newspaper, description: "News from the Decade community. Members can discuss each item in the comments.", photo: photos.iceCrystal },
    { view: "Calendar", label: "Calendar", icon: CalendarDays, description: "Decade events and meetings, shown in your time zone.", photo: photos.blueIce },
  ] },
  { label: "Network", items: [
    { view: "Members", label: "Members", icon: Users, description: "Find members by expertise, Working Group, region and availability.", photo: photos.icebergSpires },
    { view: "Working Groups", label: "Working Groups", icon: Layers, description: "From science to action: the five Working Groups of the Decade.", photo: photos.icebergsAerial },
    { view: "Opportunities", label: "Activities", icon: Briefcase, description: "Concrete contributions open to every member, often part of a flagship project. Answer an open call, or propose an activity of your own.", photo: photos.icebergSky },
    { view: "Messages", label: "Messages", icon: MessageCircle, description: "Private conversations with other members of the Decade community.", photo: photos.iceCave },
    { view: "My contributions", label: "My contributions", icon: FileCheck, description: "Your expressions of interest and the work agreed with Working Groups.", photo: photos.iceCave },
  ] },
  { label: "Coordination", items: [
    { view: "Task boards", label: "Task boards", icon: SquareKanban, description: "Day-to-day coordination of the leadership and Core Groups: who does what, and by when.", photo: photos.icebergFjord },
    { view: "Meeting polls", label: "Polls & consultations", icon: CalendarClock, description: "Find a meeting time across time zones, or consult your group with a yes/no vote or a short survey.", photo: photos.iceCave },
    { view: "Work plans", label: "Flagship projects", title: "Flagship projects", icon: Rocket, description: "The strategic projects the Working Groups lead to achieve each main goal of the Decade, with their milestones and the activities that contribute to them.", photo: photos.icebergsAerial },
    { view: "Decision register", label: "Decision register", icon: BookMarked, description: "Decisions of the Strategic Management Committee and the Executive Steering Committee, with links to the minutes.", photo: photos.icebergSky },
    { view: "Mailing lists", label: "Mailing lists", icon: Mail, description: "Write in one click, in Bcc, to the leadership, the Core Group or the Broad Group of the groups you lead.", photo: photos.icebergsAerial },
    { view: "Logo review", label: "Logo review", icon: BadgeCheck, description: "Assessment of requests to carry the logo of the Decade.", photo: photos.icebergSky },
    { view: "Core Group workspace", label: "SharePoint library", title: "SharePoint library", icon: FolderOpen, description: "The working documents of the Decade bodies on SharePoint, and the shortcut to Microsoft Teams.", photo: photos.icebergsAerial },
    { view: "Governance", label: "Governance", icon: Network, description: "Governance model of the Decade. Open the space of a body, or select it in the chart to view its appointments.", photo: photos.icebergFjord },
  ] },
  { label: "The Decade", items: [
    { view: "Decade timeline", label: "Decade timeline", icon: Milestone, description: "The Decade from 2025 to 2034: its three triennia, today, and the events and decisions along the way.", photo: photos.blueIce },
    { view: "Official Decade website", label: "Official website", title: "Official Decade website", icon: Globe, description: "The public website of the Decade, its content submission form and the logo application.", photo: photos.icebergSpires },
    { view: "Templates", label: "Templates", icon: Presentation, description: "The presentation template of the Decade and its logo in the six official languages of the United Nations, for the Core Group and the leadership of the Decade bodies.", photo: photos.iceCrystal },
  ] },
  { label: "Administration", items: [
    { view: "Dashboard", label: "Dashboard", icon: ChartNoAxesCombined, description: "Membership, meeting rhythm, pending reviews and logo deadlines, with CSV exports, the members map and the weekly digest.", photo: photos.iceCrystal },
    { view: "Chat moderation", label: "Chat moderation", icon: ShieldAlert, description: "Reports on private conversations, the conversations themselves and the team of moderators.", photo: photos.blueIce },
    { view: "UNESCO Secretariat", label: "UNESCO Secretariat", icon: ShieldCheck, description: "Members, content, access, badges and shared categories.", photo: photos.blueIce },
  ] },
];
const otherViews: Partial<Record<View, { label: string; description: string; photo: Photo }>> = {
  "Find expertise": { label: "Find expertise", description: "Match members to an activity. Skills 60% · Working Group interest 20% · region 10% · language 10%.", photo: photos.icebergSpires },
  "My profile": { label: "My profile", description: "Your expertise, interests and visibility. Appointments are assigned separately by the Secretariat.", photo: photos.iceCrystal },
};
const viewInfo = (v: View) => {
  const item = navGroups.flatMap((g) => g.items).find((i) => i.view === v);
  return item ? { label: item.label, title: item.title || item.label, description: item.description, photo: item.photo } : { label: otherViews[v]?.label || v, title: otherViews[v]?.label || v, description: otherViews[v]?.description || "", photo: otherViews[v]?.photo || photos.icebergFjord };
};
const blank = blankProfile;
const blankActivity = { title: "", description: "", wg: 1, skills: [] as string[], region: "Global", language: "English", commitment: "2–4 hours / month", deadline: "", type: "Scientific review", mgs: [] as string[], project: "" };
const icons = [Satellite, ChartNoAxesCombined, Shield, Leaf, Megaphone];
const date = (s: string) =>
  new Date(s).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
function Pick({
  value,
  onChange,
  items,
  label,
  className = "",
}: {
  value: string;
  onChange: (v: string) => void;
  items: { value: string; label: string }[];
  label: string;
  className?: string;
}) {
  return (
    <Select value={value || undefined} onValueChange={onChange}>
      <SelectTrigger
        aria-label={label}
        className={"select-control " + className}
      >
        <SelectValue placeholder={label} />
      </SelectTrigger>
      <SelectContent>
        {items.map((x) => (
          <SelectItem key={x.value} value={x.value}>
            {x.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
const opts = (a: string[]) => a.map((x) => ({ value: x, label: x }));
const Avatar = MemberAvatar;
function WgPill({ wg }: { wg: number }) {
  const g = groups.find((x) => x.id === wg);
  return g ? (
    <span className="pill wg" style={{ "--wg-color": g.color } as any}>
      WG{wg} · {g.short}
    </span>
  ) : (
    <span className="pill">Decade-wide</span>
  );
}
function Empty({
  title,
  text,
  children,
  icon: Icon = Snowflake,
}: {
  title: string;
  text: string;
  children?: React.ReactNode;
  icon?: LucideIcon;
}) {
  return (
    <div className="empty-state">
      <Icon size={26} />
      <h3>{title}</h3>
      <p>{text}</p>
      {children}
    </div>
  );
}
function StatTile({ value, label, Icon, accent, onClick }: { value: number; label: string; Icon: LucideIcon; accent?: string; onClick?: () => void }) {
  const shown = useCountUp(value);
  const body = (
    <>
      <span className="stat-icon"><Icon size={22} /></span>
      <div>
        <b>{shown}</b>
        <span>{label}</span>
      </div>
    </>
  );
  const style = accent ? ({ "--stat-accent": accent } as React.CSSProperties) : undefined;
  return onClick ? (
    <button type="button" className="glass stat" style={style} onClick={onClick} aria-label={`${value} ${label}`}>{body}</button>
  ) : (
    <div className="glass stat" style={style}>{body}</div>
  );
}
function SkeletonPage() {
  return (
    <div className="stack" aria-hidden="true">
      <div className="stats">
        {[0, 1, 2].map((i) => (
          <div key={i} className="glass stat">
            <span className="skeleton" style={{ width: 46, height: 46, borderRadius: 12 }} />
            <div style={{ flex: 1, display: "grid", gap: 8 }}>
              <span className="skeleton skeleton-line" style={{ width: "35%", height: 22 }} />
              <span className="skeleton skeleton-line" style={{ width: "65%" }} />
            </div>
          </div>
        ))}
      </div>
      <div className="op-grid">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="glass skeleton-card">
            <span className="skeleton skeleton-line" style={{ width: "30%" }} />
            <span className="skeleton skeleton-line" style={{ width: "85%", height: 16 }} />
            <span className="skeleton skeleton-line" style={{ width: "95%" }} />
            <span className="skeleton skeleton-line" style={{ width: "60%" }} />
          </div>
        ))}
      </div>
    </div>
  );
}
function NavList({
  view,
  navigate,
  visible,
  counts,
}: {
  view: View;
  navigate: (v: View) => void;
  visible: (v: View) => boolean;
  counts: Partial<Record<View, number>>;
}) {
  return (
    <nav className="side-nav" aria-label="Main navigation">
      {navGroups.map((group) => {
        const items = group.items.filter((i) => visible(i.view));
        if (!items.length) return null;
        return (
          <div className="nav-group" key={group.label}>
            <div className="nav-group-label">{group.label}</div>
            {items.map((item) => {
              const active = view === item.view || (item.view === "Opportunities" && view === "Find expertise");
              return (
                <button
                  key={item.view}
                  className={"nav-button " + (active ? "active" : "")}
                  aria-current={active ? "page" : undefined}
                  onClick={() => navigate(item.view)}
                >
                  <item.icon size={18} />
                  {item.label}
                  {counts[item.view] !== undefined && (
                    <span className="nav-count">{counts[item.view]}</span>
                  )}
                </button>
              );
            })}
          </div>
        );
      })}
    </nav>
  );
}
function MeCard({ me, onOpen }: { me: any; onOpen: () => void }) {
  return (
    <button className="me-card" onClick={onOpen}>
      <Avatar name={me?.name || "Guest"} uid={me?.id} hasPhoto={me?.hasPhoto} version={me?.updatedAt} />
      <div>
        <strong>{me?.name || "Your Decade profile"}</strong>
        <span>{me ? me.membershipBadges?.[0]?.label || "Interested member" : "Create your member profile"}</span>
      </div>
    </button>
  );
}
function AccountMenu({ me, email, light, toggleTheme, navigate, onWelcome }: { me: any; email: string; light: boolean; toggleTheme: () => void; navigate: (v: View) => void; onWelcome?: () => void }) {
  const first = (me?.name || "").split(" ")[0] || "Account";
  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger asChild>
        <button className="account-trigger" aria-label="Account menu">
          <Avatar name={me?.name || email || "?"} uid={me?.id} hasPhoto={me?.hasPhoto} version={me?.updatedAt} />
          <span className="account-name">{first}</span>
          <ChevronDown size={16} />
        </button>
      </DropdownMenu.Trigger>
      <DropdownMenu.Portal>
        <DropdownMenu.Content className="menu-content" align="end" sideOffset={10}>
          <div className="menu-header">
            <Avatar name={me?.name || email || "?"} uid={me?.id} hasPhoto={me?.hasPhoto} version={me?.updatedAt} />
            <div>
              <strong>{me?.name || "Your account"}</strong>
              <span title={email}>{email}</span>
            </div>
          </div>
          <DropdownMenu.Item className="menu-item" onSelect={() => navigate("My profile")}>
            <UserRound size={16} />
            {me ? "My profile" : "Create profile"}
          </DropdownMenu.Item>
          {me && onWelcome && (
            <DropdownMenu.Item className="menu-item" onSelect={onWelcome}>
              <PlayCircle size={16} />
              Watch the welcome video
            </DropdownMenu.Item>
          )}
          <DropdownMenu.Item className="menu-item" onSelect={() => navigate("My contributions")}>
            <FileCheck size={16} />
            My contributions
          </DropdownMenu.Item>
          <DropdownMenu.Item className="menu-item" onSelect={(e) => { e.preventDefault(); toggleTheme(); }}>
            {light ? <Moon size={16} /> : <Sun size={16} />}
            {light ? "Dark mode" : "Light mode"}
          </DropdownMenu.Item>
          <DropdownMenu.Separator className="menu-separator" />
          <DropdownMenu.Item className="menu-item danger" onSelect={signOutMember}>
            <LogOut size={16} />
            Sign out
          </DropdownMenu.Item>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}
export default function Community({ signedIn }: { signedIn: boolean }) {
  const { user: firebaseUser, openSignIn } = useMemberAuth();
  const [view, setView] = useState<View>("Community"),
    [data, setData] = useState<any>({
      people: [],
      opportunities: [],
      contributions: [],
      posts: [],
      follows: [],
      governance: [],
      events: [],
      me: null,
      admin: false,
      user: null,
    }),
    [loading, setLoading] = useState(signedIn),
    [refreshing, setRefreshing] = useState(false),
    [error, setError] = useState(""),
    [light, setLight] = useState(() => storedTheme() === "light"),
    [navOpen, setNavOpen] = useState(false),
    [query, setQuery] = useState(""),
    [wgFilter, setWgFilter] = useState("all"),
    [regionFilter, setRegionFilter] = useState("all"),
    [skillFilter, setSkillFilter] = useState("all"),
    [availabilityFilter, setAvailabilityFilter] = useState("all"),
    [selected, setSelected] = useState<any>(null),
    [opDetail, setOpDetail] = useState<any>(null),
    [editingOp, setEditingOp] = useState<string | null>(null),
    [activeGroup, setActiveGroup] = useState<number | null>(null),
    [activeBody, setActiveBody] = useState<string | null>(null),
    [discussionFocus, setDiscussionFocus] = useState<string | undefined>(),
    [modal, setModal] = useState<"post" | "opportunity" | "apply" | null>(null),
    [saving, setSaving] = useState(false),
    [draft, setDraft] = useState<any>(blank),
    [body, setBody] = useState(""),
    [postWg, setPostWg] = useState("0"),
    [postMgs,setPostMgs] = useState<string[]>([...allGoalIds]),
    [postFiles,setPostFiles] = useState<Attachment[]>([]),
    [feedMode, setFeedMode] = useState("all"),
    [matchOp, setMatchOp] = useState(""),
    [opDraft, setOpDraft] = useState<any>(blankActivity);
  const { scrolled, showTop } = useScrollFlags();
  const access=useMeetingAccess(firebaseUser?.uid||"",data.me);
  const meetingTools=useMeetingTools(access);
  const consultationTools=useConsultations(access);
  const [myActions,setMyActions]=useState<ActionItem[]>([]);
  useEffect(()=>{setMyActions([]);if(!firebaseUser?.uid||data.me?.onboardingVersion!==2)return;return subscribeMyActions(firebaseUser.uid,setMyActions,()=>setMyActions([]));},[firebaseUser?.uid,data.me?.onboardingVersion]);
  const [memberMode,setMemberMode]=useState<"list"|"map">("list");
  const [memberStats,setMemberStats]=useState<MemberStats|null>(null);
  useEffect(()=>{setMemberStats(null);if(!firebaseUser?.uid||data.me?.onboardingVersion!==2)return;return subscribeMemberStats(setMemberStats,()=>setMemberStats(null));},[firebaseUser?.uid,data.me?.onboardingVersion]);
  const statsPublished=useRef(false);
  useEffect(()=>{if(memberMode!=="map"||!data.admin||statsPublished.current)return;statsPublished.current=true;void publishMemberStats().catch(()=>{});},[memberMode,data.admin]);
  const [pollTab,setPollTab]=useState<"polls"|"consultations">("polls");
  const [consultationFocus,setConsultationFocus]=useState<string|undefined>();
  // Three-week meeting reminder: a pop-up at sign-in for the Leads, Associate Leads and Secretariat of a group
  // whose last meeting was 21 or more days ago, with no meeting or open poll planned. UNESCO access alone does not count.
  const ownLeadership = useCallback((id: string) => {
    const role = isUnescoSecretariat(access.role || {}) ? { ...access.role, role: "member", admin: false, badges: [] } : access.role;
    return bodyLevel({ ...access, admin: false, role }, id) >= 3;
  }, [access]);
  const dueMeetings = meetingTools.reminders.filter((r: any) => ownLeadership(r.id));
  const [meetingNudge, setMeetingNudge] = useState<any[] | null>(null);
  const [meetingSeed,setMeetingSeed]=useState<MeetingSeed|undefined>();
  const [pollFocus,setPollFocus]=useState<string|undefined>(),[pollBody,setPollBody]=useState<string|undefined>();
  const [calendarFocus, setCalendarFocus] = useState<CalendarEvent | undefined>();
  // Mentions in Working Group discussions (Hub notifications).
  const uid = firebaseUser?.uid || "";
  const hubReady = data.me?.onboardingVersion === 2;
  const [inbox, setInbox] = useState<InboxItem[] | null>(null);
  const seenMentions = useRef<Set<string> | null>(null);
  useEffect(() => {
    setInbox(null);
    seenMentions.current = null;
    if (!uid || !hubReady) return;
    return subscribeInbox(uid, setInbox, () => setInbox([]));
  }, [uid, hubReady]);
  const [categories, setCategories] = useState<any[]>([]);
  useEffect(
    () =>
      subscribeCategories(setCategories, (e) => toast.error(friendlyError(e))),
    [],
  );
  const allSkills = optionsFor("skills", categories);
  const loadingRef = useRef(false);
  const load = useCallback(async (background = false) => {
    if (!signedIn || loadingRef.current) return;
    loadingRef.current = true;
    if (!background) setError("");
    try {
      const d: any = await loadCommunity();
      setData(d);
      setError("");
      if (!background) setDraft(
        d.me ? { ...blank, ...d.me } : { ...blank, name: d.user?.name || "" },
      );
    } catch (e: any) {
      setError(friendlyError(e));
    } finally {
      loadingRef.current = false;
      setLoading(false);
    }
  }, [signedIn]);
  async function refresh() {
    setRefreshing(true);
    try {
      await load();
    } finally {
      setRefreshing(false);
    }
  }
  useEffect(() => {
    load();
  }, [load]);
  useEffect(() => {
    const refresh = () => {
      if (document.visibilityState !== "visible" || !navigator.onLine ||
        saving || loading || modal || view === "My profile" ||
        !data.me || data.me.onboardingVersion !== 2 ||
        document.querySelector('[role="dialog"]')) return;
      void load(true);
    };
    const timer = window.setInterval(refresh, 60_000);
    return () => window.clearInterval(timer);
  }, [load, saving, loading, modal, view, data.me?.id, data.me?.onboardingVersion]);
  // Templates: the Core Group and the leadership of the Working Groups and of the other Decade bodies.
  const templatesAccess = !!data.me?.id && (data.admin || data.canAccessWorkspace === true || meetingBodies.some((b) => bodyLevel(access, b.id) >= 2));
  useEffect(() => {
    if ((view === "Core Group workspace" && !data.canAccessWorkspace) ||
      ((view === "UNESCO Secretariat" || view === "Dashboard") && !data.admin) || (view === "Logo review" && !canReviewLogo(access)) ||
      (view === "Mailing lists" && !loading && !data.admin && !mailingAccess(access).length) ||
      (view === "Templates" && !loading && !templatesAccess)) setView("Community");
  }, [view, data.canAccessWorkspace, data.admin,access,loading,templatesAccess]);
  // Mailing lists: keep this member's own entries in line with their groups and roles.
  useEffect(() => {
    if (!data.me?.id || !data.user?.email || data.me.onboardingVersion !== 2) return;
    syncOwnEntries(data.me, data.user.email, data.governance || []).catch(() => {});
  }, [data.me, data.user?.email, data.governance]);
  // Roles declared by members, awaiting the UNESCO Secretariat.
  const [pendingRoles, setPendingRoles] = useState(0);
  const viewRef = useRef(view);
  viewRef.current = view;
  // Private messages and their moderation.
  const [chats, setChats] = useState<Chat[]>([]), [chatTarget, setChatTarget] = useState<any>(null);
  const [monitors, setMonitors] = useState<string[]>([]), [reports, setReports] = useState<ChatReport[]>([]);
  const myId = data.me?.id || "";
  const chatOwner = !!myId && isOwnerAccount();
  const monitor = chatOwner || (!!myId && monitors.includes(myId));
  const seenChats = useRef<Record<string, string> | null>(null), seenReports = useRef<Set<string> | null>(null);
  useEffect(() => {
    setChats([]); seenChats.current = null;
    if (!myId || data.me?.onboardingVersion !== 2) return;
    return subscribeMyChats(myId, (list) => {
      // A short notice when a new message arrives, except while the member is reading their messages.
      const before = seenChats.current;
      if (before && viewRef.current !== "Messages") {
        const fresh = list.find((c) => isUnread(c, myId) && before[c.id] !== c.updatedAt);
        if (fresh) toast.info(isGroup(fresh) ? `New message in ${fresh.title || "a group conversation"}` : `New message from ${fresh.names?.[otherMember(fresh, myId)] || "a member"}`, { description: fresh.lastMessage?.text ? (fresh.lastMessage.text.length > 110 ? fresh.lastMessage.text.slice(0, 109) + "…" : fresh.lastMessage.text) : undefined, action: { label: "Open", onClick: () => { setChatTarget({ chatId: fresh.id }); setView("Messages"); } } });
      }
      seenChats.current = Object.fromEntries(list.map((c) => [c.id, c.updatedAt]));
      setChats(list);
    }, () => setChats([]));
  }, [myId, data.me?.onboardingVersion]);
  useEffect(() => { if (!myId) { setMonitors([]); return; } return subscribeMonitors(setMonitors, () => setMonitors([])); }, [myId]);
  useEffect(() => {
    setReports([]); seenReports.current = null;
    if (!monitor) return;
    return subscribeReports((list) => {
      const before = seenReports.current;
      const fresh = before ? list.filter((r) => r.status === "open" && !before.has(r.id)) : [];
      if (fresh.length) toast.warning(`${fresh.length === 1 ? "A conversation was" : fresh.length + " conversations were"} reported`, { action: { label: "Review", onClick: () => setView("Chat moderation") } });
      seenReports.current = new Set(list.map((r) => r.id));
      setReports(list);
    }, () => setReports([]));
  }, [monitor]);
  // Flagship projects and milestones of the Working Groups (work plan items).
  const [workItems, setWorkItems] = useState<WorkItem[] | null>(null), [workError, setWorkError] = useState("");
  useEffect(() => { setWorkItems(null); if (!myId) return; return subscribeWorkplan(setWorkItems, (e) => setWorkError(friendlyError(e))); }, [myId]);
  // Member badge on a lanyard beside a profile, on wide screens.
  const lanyardSpace = useLanyardSpace();
  const [wgTab, setWgTab] = useState<WgTab>("overview"), nextWgTab = useRef<WgTab | undefined>(undefined);
  useEffect(() => { setWgTab(nextWgTab.current || "overview"); nextWgTab.current = undefined; }, [activeGroup]);
  /** Opens a tab of a Working Group page from anywhere in the platform. */
  const openGroupTab = (n: number, tab: WgTab) => { navigate("Working Groups"); nextWgTab.current = tab; setActiveGroup(n); if (activeGroup === n) { nextWgTab.current = undefined; setWgTab(tab); } };
  useEffect(() => { if (discussionFocus && activeGroup) setWgTab("discussion"); }, [discussionFocus, activeGroup]);
  // Broad Group membership of each Working Group: certified by a badge from the UNESCO Secretariat, applied for, or neither.
  const [ownRequest, setOwnRequest] = useState<RoleRequest | null>(null);
  useEffect(() => { setOwnRequest(null); if (!myId) return; return subscribeOwnRequest(myId, setOwnRequest, () => setOwnRequest(null)); }, [myId]);
  const groupStanding = (person: any, n: number) => {
    const ids = (person?.membershipBadges || []).map((b: any) => b.id);
    if (["lead", "associate", "secretariat", "core"].some((r) => ids.includes(`wg${n}-${r}`))) return "core" as const;
    if (ids.includes(`wg${n}-member`)) return "broad" as const;
    return (person?.wgs || []).includes(n) ? "interested" as const : null;
  };
  // Applications to the Broad Groups: the member's own, those awaiting the UNESCO Secretariat, and those of the group shown to its leadership.
  const [ownApps, setOwnApps] = useState<Application[]>([]), [pendingApps, setPendingApps] = useState<Application[]>([]);
  const [groupApps, setGroupApps] = useState<Application[]>([]), [ledApps, setLedApps] = useState<Application[]>([]);
  useEffect(() => { setOwnApps([]); if (!myId) return; return subscribeOwnApplications(myId, setOwnApps, () => setOwnApps([])); }, [myId]);
  useEffect(() => { setPendingApps([]); if (!myId || !data.admin) return; return subscribePendingApplications(setPendingApps, () => setPendingApps([])); }, [myId, data.admin]);
  const ledWgs = useMemo(() => [1, 2, 3, 4, 5].filter((n) => bodyLevel(access, "wg" + n) >= 3), [access]);
  const leadsActive = !!activeGroup && (data.admin || ledWgs.includes(activeGroup));
  useEffect(() => { setGroupApps([]); if (!myId || !activeGroup || !leadsActive) return; return subscribeBodyApplications("wg" + activeGroup, setGroupApps, () => setGroupApps([])); }, [myId, activeGroup, leadsActive]);
  // Leaders hear about new applications to the groups they lead, wherever they are in the platform.
  const seenLed = useRef<Set<string> | null>(null);
  useEffect(() => {
    setLedApps([]); seenLed.current = null;
    if (!myId || data.admin || !ledWgs.length) return;
    const lists: Record<string, Application[]> = {};
    const stops = ledWgs.map((n) => subscribeBodyApplications("wg" + n, (list) => {
      lists[n] = list.filter((a) => a.status === "pending");
      const all = Object.values(lists).flat(), known = seenLed.current;
      const fresh = known ? all.filter((a) => !known.has(a.id)) : [];
      if (fresh.length) toast.info(fresh.length === 1 ? `${fresh[0].name} applied to join the WG${fresh[0].body.slice(2)} Broad Group` : `${fresh.length} new applications to join a Broad Group`, { action: { label: "Review", onClick: () => { openGroupTab(Number(fresh[0].body.slice(2)), "requests"); } } });
      seenLed.current = new Set(all.map((a) => a.id));
      setLedApps(all);
    }, () => {}));
    return () => stops.forEach((s) => s());
  }, [myId, data.admin, ledWgs.join(",")]);
  // A welcome moment, once per device, for an application approved in the last 60 days.
  const [celebrate, setCelebrate] = useState<Application | null>(null);
  useEffect(() => {
    if (!myId || !data.me || celebrate) return;
    const seen = celebrated(myId), since = Date.now() - 60 * 86400000;
    const a = ownApps.find((x) => x.status === "approved" && !seen.includes(x.id) && (!x.decidedAt || Date.parse(x.decidedAt) > since));
    if (a) setCelebrate(a);
  }, [ownApps, myId, !!data.me]);
  const broadStatus = (n: number) => {
    const standing = groupStanding(data.me, n);
    if (standing === "core" || standing === "broad") return "member";
    const app = ownApps.find((a) => a.body === "wg" + n);
    if (app?.status === "pending") return "pending";
    if (app?.status === "declined") return "declined";
    // Applications declared at registration, before applications had their own requests.
    const c = ownRequest?.claims?.["wg" + n], d = ownRequest?.decisions?.["wg" + n];
    if (c && !d) return "pending";
    return d === "declined" ? "declined" : "none";
  };
  async function applyBroad(n: number) {
    if (!requireProfile()) return;
    try {
      await applyToGroup("wg" + n, data.me.name);
      toast.success(`Your application to the WG${n} Broad Group has been sent.`, { description: "The leadership of the group and the UNESCO Secretariat will review it. You will see the Broad Group badge on your profile once it is approved." });
    } catch (e: any) {
      if (e?.code === "permission-denied") toast.error("Your application could not be sent.", { description: "Please try again in a few minutes. If the problem continues, contact the UNESCO Secretariat at cryosphere@unesco.org." });
      else toast.error(friendlyError(e));
    }
  }
  const projectTitle = (id?: string) => (id && workItems?.find((i) => i.id === id && i.kind === "deliverable")?.title) || "";
  // Tasks assigned to the member: a notice for each new assignment and, once per session, for deadlines that are close.
  const [myTasks, setMyTasks] = useState<Task[]>([]), [taskFocus, setTaskFocus] = useState<string | undefined>();
  const seenTasks = useRef<Set<string> | null>(null);
  useEffect(() => {
    setMyTasks([]); seenTasks.current = null;
    if (!myId || data.me?.onboardingVersion !== 2) return;
    return subscribeMyTasks(myId, (list) => {
      const known = seenTasks.current, today = localToday();
      const fresh = list.filter((t) => isNewFor(t, myId) && t.updatedBy !== myId && (!known || !known.has(t.id)));
      if (fresh.length === 1) toast.info(`New task: ${fresh[0].title}`, { description: `${bodyLabel(fresh[0].body)}${fresh[0].due ? " · " + dueLabel(fresh[0].due, today) : ""}`, action: { label: "Open", onClick: () => { navigate("Task boards"); setTaskFocus("mine"); } } });
      else if (fresh.length > 1) toast.info(`${fresh.length} new tasks are assigned to you.`, { action: { label: "Open", onClick: () => { navigate("Task boards"); setTaskFocus("mine"); } } });
      if (!known) {
        const urgent = list.filter((t) => ["soon", "overdue"].includes(dueState(t, today)));
        let shown = ""; try { shown = sessionStorage.getItem("dacs-task-deadlines-" + myId) || ""; } catch { /* storage unavailable */ }
        const ids = urgent.map((t) => t.id + dueState(t, today)).sort().join("|");
        if (urgent.length && shown !== ids) {
          try { sessionStorage.setItem("dacs-task-deadlines-" + myId, ids); } catch { /* storage unavailable */ }
          const overdue = urgent.filter((t) => dueState(t, today) === "overdue").length;
          toast.warning(urgent.length === 1 ? `${urgent[0].title}: ${dueLabel(urgent[0].due, today).toLowerCase()}` : `${urgent.length} of your tasks are due soon${overdue ? `, ${overdue} overdue` : ""}.`, { action: { label: "View", onClick: () => { navigate("Task boards"); setTaskFocus("mine"); } } });
        }
      }
      seenTasks.current = new Set(list.filter((t) => isNewFor(t, myId)).map((t) => t.id));
      setMyTasks(list);
    }, () => setMyTasks([]));
  }, [myId, data.me?.onboardingVersion]);
  const bellTasks = (() => {
    const today = localToday();
    return myTasks.filter((t) => t.status !== "done").flatMap((t) => {
      const state = dueState(t, today), fresh = isNewFor(t, myId);
      if (!fresh && state !== "soon" && state !== "overdue") return [];
      return [{ id: t.id, key: "k:" + t.id + ":" + (fresh ? "new" : state), title: t.title, sub: `${bodyLabel(t.body)}${t.due ? " · " + dueLabel(t.due, today) : ""}`, state: fresh ? "new" as const : state as "soon" | "overdue", body: t.body }];
    });
  })();
  const unreadChats = chats.filter((c) => isUnread(c, myId)).length;
  const openReports = reports.filter((r) => r.status === "open").length;
  // Notification centre: conversations, and what is new in the Working Groups the member follows.
  const bellMessages = chats.filter((c) => isUnread(c, myId)).slice(0, 12).map((c) => {
    const sm = chatSummary(c, myId, data.people || []);
    return { id: c.id, title: sm.title, text: sm.text, when: c.updatedAt, unread: isUnread(c, myId), group: isGroup(c), uid: isGroup(c) ? undefined : otherMember(c, myId) };
  });
  const followed: number[] = data.follows?.length ? data.follows : data.me?.wgs || [];
  const bellUpdates = (() => {
    if (!data.me) return [];
    const now = Date.now(), since = now - 21 * 86400000, soon = now + 21 * 86400000;
    const inFollowed = (wgs: number[]) => wgs.some((w) => followed.includes(w));
    const day = (v: string) => new Date(v).toLocaleDateString("en-GB", { weekday: "short", day: "numeric", month: "short" });
    const news = (data.posts || []).filter((p: any) => Date.parse(p.created_at || p.createdAt) >= since && p.author !== myId
      && (p.wg === 0 || isDecadeWide(p.mgs) || inFollowed([p.wg, ...linkedGroups(p.mgs || [])])))
      .map((p: any) => ({ id: "n" + p.id, kind: "news" as const, title: p.title || String(p.body).slice(0, 90), sub: `${p.author_name} · ${day(p.created_at || p.createdAt)}`, stamp: String(p.created_at || p.createdAt), tag: p.wg ? `WG${p.wg}` : "Decade", style: accentStyle({ ocs: p.wg ? [p.wg] : [1, 2, 3, 4, 5] }), open: () => navigate("News") }));
    const events = (data.events || []).filter((e: any) => Date.parse(e.startAt) >= now - 3600000 && Date.parse(e.startAt) <= soon && (isDecadeWide(e.mgs) || inFollowed(e.ocs || [])))
      .map((e: any) => ({ id: "e" + e.id, kind: "event" as const, title: e.title, sub: `${day(e.startAt)} · ${new Date(e.startAt).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })}`, stamp: String(e.createdAt || e.startAt), tag: eventAccent(e).tag, style: accentStyle(e), open: () => void openMeeting(e.id) }));
    const activities = (data.opportunities || []).filter((o: any) => o.status === "open" && Date.parse(o.createdAt) >= since && o.owner !== myId && inFollowed(activityGroups(o)))
      .map((o: any) => ({ id: "a" + o.id, kind: "activity" as const, title: o.title, sub: `${o.type} · ${o.commitment}`, stamp: String(o.createdAt), tag: `WG${o.wg}`, style: accentStyle({ ocs: [o.wg] }), open: () => setOpDetail(o) }));
    return [...news, ...events, ...activities].sort((a, b) => b.stamp.localeCompare(a.stamp)).slice(0, 12);
  })();
  function openChat(person: any) { setChatTarget(person); navigate("Messages"); }
  // Welcome video: opens once, after the member's first sign-in with a completed profile.
  const [welcome, setWelcome] = useState(false);
  const [tor, setTor] = useState<string | null>(null);
  const welcomeKey = "dacs-welcome-" + myId;
  useEffect(() => {
    if (!myId || data.me?.onboardingVersion !== 2 || data.welcomeSeen !== false) return;
    try { if (localStorage.getItem(welcomeKey)) return; } catch { /* storage unavailable */ }
    setWelcome(true);
  }, [myId, data.me?.onboardingVersion, data.welcomeSeen]);
  function closeWelcome() {
    setWelcome(false);
    try { localStorage.setItem(welcomeKey, "1"); } catch { /* storage unavailable */ }
    if (data.welcomeSeen === false) saveCommunity({ action: "welcomeSeen" }).catch(() => {});
  }
  useEffect(() => {
    if (!data.admin) { setPendingRoles(0); return; }
    return subscribePendingRequests((r) => setPendingRoles(r.length), () => setPendingRoles(0));
  }, [data.admin]);
  function toggleTheme() {
    const v = !light;
    setLight(v);
    saveTheme(v ? "light" : "dark");
    auroraSweep();
  }
  function navigate(v: View) {
    setView(v);
    setNavOpen(false);
    setCalendarFocus(undefined);setMeetingSeed(undefined);setPollFocus(undefined);setPollBody(undefined);
    setActiveGroup(null);
    setActiveBody(null);
    setTaskFocus(undefined);
    setDiscussionFocus(undefined);
    setPollTab("polls");
    setConsultationFocus(undefined);
    setQuery("");
    setWgFilter("all");
    setRegionFilter("all");
    setSkillFilter("all");
    setAvailabilityFilter("all");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
  function openGroup(id: number | null) {
    setActiveGroup(id);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
  function openBody(id: string | null) {
    setActiveBody(id);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
  /** Opens a governing body space; Working Groups open their own space. */
  function openSpace(id: string) {
    if (/^wg[1-5]$/.test(id)) {
      navigate("Working Groups");
      setActiveGroup(Number(id[2]));
    } else openBody(id);
  }
  const spaceLabel = (space: string) => {
    const g = groups[Number(space.slice(2)) - 1];
    return g ? `WG${g.id} · ${g.short}` : space;
  };
  /** Opens a meeting (and its minutes) in the Calendar. */
  async function openMeeting(eventId: string) {
    try {
      const ev = await fetchEvent(eventId);
      if (!ev) return toast.info("This meeting is no longer in the calendar.");
      navigate("Calendar");
      setCalendarFocus(ev);
    } catch (e) {
      toast.error(friendlyError(e));
    }
  }
  function openConsultation(id: string) {
    navigate("Meeting polls");
    setPollTab("consultations");
    setConsultationFocus(id);
  }
  function openMention(item: InboxItem) {
    navigate("Working Groups");
    setActiveGroup(Number(item.space.slice(2)));
    setDiscussionFocus(item.messageId);
    if (!item.read) void markRead(uid, [item.id]).catch(() => {});
  }
  // Announce mentions: one summary after sign-in, then each new mention as it arrives.
  useEffect(() => {
    if (!inbox) return;
    const unread = inbox.filter((i) => !i.read);
    if (!seenMentions.current) {
      seenMentions.current = new Set(inbox.map((i) => i.id));
      const ids = unread.map((i) => i.id).sort().join("|");
      let shown = "";
      try { shown = sessionStorage.getItem("dacs-mention-notice-" + uid) || ""; } catch {}
      if (!unread.length || shown === ids) return;
      try { sessionStorage.setItem("dacs-mention-notice-" + uid, ids); } catch {}
      if (unread.length === 1)
        toast.info(`${unread[0].from_name} mentioned you in ${spaceLabel(unread[0].space)}.`, { action: { label: "View", onClick: () => openMention(unread[0]) } });
      else toast.info(`You have ${unread.length} unread mentions. Open the bell to view them.`);
      return;
    }
    for (const item of unread.filter((i) => !seenMentions.current!.has(i.id)).slice(0, 3))
      toast.info(`${item.from_name} mentioned you in ${spaceLabel(item.space)}`, {
        description: item.excerpt.length > 120 ? item.excerpt.slice(0, 119) + "…" : item.excerpt,
        action: { label: "View", onClick: () => openMention(item) },
      });
    inbox.forEach((i) => seenMentions.current!.add(i.id));
  }, [inbox]);
  const dueKey = dueMeetings.map((r: any) => r.id).sort().join("|");
  useEffect(() => {
    if (!uid || !hubReady || !dueKey) return;
    const key = "dacs-meeting-popup-" + uid;
    let shown = "";
    try { shown = sessionStorage.getItem(key) || ""; } catch {}
    if (shown === dueKey) return;
    try { sessionStorage.setItem(key, dueKey); } catch {}
    setMeetingNudge(dueMeetings);
  }, [uid, hubReady, dueKey]);
  async function mutate(payload: any, success: string) {
    if (!signedIn) {
      toast.info("Sign in to save your contribution.");
      return false;
    }
    setSaving(true);
    try {
      const d: any = await saveCommunity(payload);
      await load();
      toast.success(
        d.pending ? "Submitted for Working Group review." : success,
      );
      return true;
    } catch (e: any) {
      toast.error(friendlyError(e));
      return false;
    } finally {
      setSaving(false);
    }
  }
  function requireProfile() {
    if (!signedIn) {
      openSignIn();
      return false;
    }
    if (!data.me) {
      navigate("My profile");
      toast.info("Create your profile to contribute.");
      return false;
    }
    return true;
  }
  function openModal(type: "post" | "opportunity" | "apply") {
    if (requireProfile()) {
      setBody("");
      setPostFiles([]);
      if (type === "opportunity") setOpDraft((d: any) => ({ ...d, attachments: [] }));
      setModal(type);
    }
  }
  const people: any[] = data.people,
    ops: any[] = data.opportunities;
  const eligible = (wg: number) =>
    data.admin || (data.me && data.me.managedWgs?.includes(wg));
  const filtered = people.filter(
    (p) =>
      (query === "" ||
        [
          p.name,
          p.headline,
          p.organisation,
          p.country,
          p.bio,
          p.careerStage,
          p.educationLevel,
          ...(p.cryosphereTypes || []),
          ...(p.skills || []),
        ]
          .join(" ")
          .toLowerCase()
          .includes(query.toLowerCase())) &&
      (wgFilter === "all" || p.wgs?.includes(Number(wgFilter))) &&
      (regionFilter === "all" || p.region === regionFilter) &&
      (skillFilter === "all" || p.skills?.includes(skillFilter)) &&
      (availabilityFilter === "all" || p.availability === availabilityFilter),
  );
  const selectedOp = ops.find((o) => o.id === matchOp) || ops[0];
  const matched = selectedOp
    ? filtered
        .map((p) => ({ ...p, match: match(p, selectedOp) }))
        .sort((a, b) => b.match.score - a.match.score)
    : [];
  const openOps = ops.filter((o) => o.status === "open");
  const myContributions = data.contributions.filter((c: any) => c.member_id === data.me?.id);
  const upcoming = (data.events || [])
    .filter((e: CalendarEvent) => Date.parse(e.endAt) >= Date.now())
    .sort((a: CalendarEvent, b: CalendarEvent) => Date.parse(a.startAt) - Date.parse(b.startAt))
    .slice(0, 4);
  useEffect(() => {
    const context = (document as any).modelContext;
    if (!context?.registerTool) return;
    const lifecycle = new AbortController();
    Promise.resolve(
      context.registerTool(
        {
          name: "search_decade_members",
          description:
            "Filter the visible member directory by expertise and Working Group.",
          inputSchema: {
            type: "object",
            properties: {
              query: { type: "string" },
              workingGroup: { type: "integer", minimum: 1, maximum: 5 },
            },
            additionalProperties: false,
          },
          annotations: { readOnlyHint: true, untrustedContentHint: true },
          execute(input: any) {
            if (
              !input ||
              typeof input !== "object" ||
              (input.query !== undefined && typeof input.query !== "string") ||
              (input.workingGroup !== undefined &&
                (!Number.isInteger(input.workingGroup) ||
                  input.workingGroup < 1 ||
                  input.workingGroup > 5))
            )
              throw new Error("Invalid member search");
            setView("Members");
            setQuery(input.query || "");
            setWgFilter(
              input.workingGroup ? String(input.workingGroup) : "all",
            );
            return {
              view: "Members",
              query: input.query || "",
              workingGroup: input.workingGroup || null,
            };
          },
        },
        { signal: lifecycle.signal },
      ),
    ).catch(() => {});
    return () => lifecycle.abort();
  }, []);
  // Render helpers (not components) so cards keep their identity between renders.
  const memberCard = (p: any) => (
    <article className="glass member-card clickable-card" key={p.id}>
      <div className="member-head">
        <Avatar
          name={p.name}
          uid={p.id}
          hasPhoto={p.hasPhoto}
          version={p.updatedAt}
        />
        <div>
          <h3>{p.name}</h3>
          {p.headline && <p>{p.headline}</p>}
        </div>
      </div>
      {(p.organisation || p.country) && (
        <div className="location">
          <MapPin size={14} />
          {[p.organisation, p.country].filter(Boolean).join(" · ")}
        </div>
      )}
      <MemberBadges badges={p.membershipBadges} compact />
      {p.skills?.length > 0 && (
        <div className="tags">
          {p.skills.slice(0, 3).map((s: string) => (
            <span className="tag" key={s}>
              {s}
            </span>
          ))}
          {p.skills.length > 3 && (
            <span className="tag">+{p.skills.length - 3}</span>
          )}
        </div>
      )}
      <div className="card-footer">
        <span>{p.availability && <><Clock size={13} />{p.availability}</>}</span>
        <button className="text-button arrow stretch" onClick={() => setSelected(p)} aria-label={"View profile of " + p.name}>
          View profile <ArrowRight size={14} />
        </button>
      </div>
    </article>
  );
  const opCard = (o: any) => {
    const owner = (data.people || []).find((p: any) => p.id === o.owner);
    const g = groups[(o.wg || 1) - 1];
    return (
      <article className={"glass op-card activity-card clickable-card " + o.status} key={o.id} style={{ "--wg-color": g.color, "--wg-ink": g.ink } as any}>
        <div className="op-card-head">
          <div className="tags">{activityGroups(o).map(wg=><WgPill key={wg} wg={wg}/>)}</div>
          <span className={"pill " + (o.status === "open" ? "green" : o.status === "pending" ? "amber" : "")}>
            {o.status === "pending" ? "Awaiting review" : o.status === "closed" ? "Closed" : "Open call"}
          </span>
        </div>
        <span className="activity-type">{o.type}</span>
        <h3>{o.title}</h3>
        {projectTitle(o.project) && <span className="op-project"><Rocket size={13} /> Part of “{projectTitle(o.project)}”</span>}
        <p className="activity-card-text">{o.description}</p>
        <GoalLabels value={o.mgs}/>
        {o.skills?.length > 0 && (
          <div className="tags">
            {o.skills.slice(0, 4).map((s: string) => <span className="tag" key={s}>{s}</span>)}
            {o.skills.length > 4 && <span className="tag">+{o.skills.length - 4}</span>}
          </div>
        )}
        <div className="op-meta">
          <span><Globe size={14} />{o.region}</span>
          <span><Clock size={14} />{o.commitment}</span>
          {o.deadline && <span><Calendar size={14} />{date(o.deadline)}</span>}
        </div>
        <div className="card-footer activity-card-foot">
          <span className="activity-owner"><Avatar name={owner?.name || "Member"} uid={o.owner} hasPhoto={owner?.hasPhoto} version={owner?.updatedAt} /><span>Proposed by<b>{owner?.name || "a member"}</b></span></span>
          <button className="btn small stretch" onClick={() => setOpDetail(o)} aria-label={"View activity: " + o.title}>
            View activity
          </button>
        </div>
      </article>
    );
  };
  const postCard = (p: any) => (
    <article className="glass post" key={p.id}>
      <div className="member-head">
        <Avatar name={p.author_name} />
        <div style={{ flex: 1 }}>
          <h3>{p.author_name}</h3>
          <div className="post-meta">{date(p.created_at)}</div>
        </div>
        {isDecadeWide(p.mgs)?<span className="pill blue">Decade-wide</span>:<WgPill wg={p.wg} />}
      </div>
      <p className="post-content">{p.body}</p><AttachmentList items={p.attachments} compact /><GoalLabels value={p.mgs}/>
    </article>
  );
  const eventCard = (event: CalendarEvent) => (
    <article className="glass op-card clickable-card" key={event.id}>
      <div className="op-card-head"><div className="tags">{event.ocs.map(wg=><WgPill key={wg} wg={wg}/>)}</div><span className="pill blue">Event</span></div>
      <h3>{event.title}</h3><p>{event.description}</p><GoalLabels value={event.mgs}/>
      <div className="op-meta"><span><Calendar size={14}/>{new Date(event.startAt).toLocaleString('en-GB',{dateStyle:'medium',timeStyle:'short'})}</span></div>
      <div className="op-meta"><CreatedBy uid={event.owner} verb="Added by" compact /></div>
      <div className="card-footer"><span>{event.location || 'Decade event'}</span><button className="btn small stretch" onClick={()=>{navigate('Calendar');setCalendarFocus(event);}}>View event</button></div>
    </article>
  );
  const realPosts = data.posts.filter(
    (p: any) =>
      (wgFilter === "all" || p.wg === Number(wgFilter) || linkedGroups(p.mgs).includes(Number(wgFilter))) &&
      (feedMode === "all" || data.follows.includes(p.wg) || linkedGroups(p.mgs).some(wg=>data.follows.includes(wg))),
  );
  const anyFilter = query || wgFilter !== "all" || regionFilter !== "all" || skillFilter !== "all" || availabilityFilter !== "all";
  function filters(matching = false) {
    return (
      <>
        <div className="filter-bar">
          <div className="toolbar">
            <div className="search-wrap">
              <Search size={17} />
              <input
                aria-label="Search members"
                type="search"
                placeholder="Search people, skills, organisations…"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </div>
            <Pick
              label="Working Group"
              value={wgFilter}
              onChange={setWgFilter}
              items={[
                { value: "all", label: "All Working Groups" },
                ...groups.map((g) => ({
                  value: String(g.id),
                  label: "WG" + g.id + " · " + g.short,
                })),
              ]}
            />
            <Pick
              label="Region"
              value={regionFilter}
              onChange={setRegionFilter}
              items={[{ value: "all", label: "All regions" }, ...opts(regions)]}
            />
          </div>
          <div className="toolbar">
            <Pick
              label="Skill"
              value={skillFilter}
              onChange={setSkillFilter}
              items={[
                { value: "all", label: "Any expertise" },
                ...opts(allSkills),
              ]}
            />
            <Pick
              label="Availability"
              value={availabilityFilter}
              onChange={setAvailabilityFilter}
              items={[
                { value: "all", label: "Any availability" },
                ...opts([
                  "2–4 hours / month",
                  "4–8 hours / month",
                  "8+ hours / month",
                  "Project-based",
                  "Currently unavailable",
                ]),
              ]}
            />
            {anyFilter && (
              <button
                className="text-button"
                onClick={() => {
                  setQuery("");
                  setWgFilter("all");
                  setRegionFilter("all");
                  setSkillFilter("all");
                  setAvailabilityFilter("all");
                }}
              >
                Clear filters
              </button>
            )}
          </div>
        </div>
        <div className="result-line" aria-live="polite">
          <span>
            <b>{filtered.length}</b> {matching ? "potential contributors" : filtered.length === 1 ? "profile" : "profiles"}
            {anyFilter ? " match your filters" : ""}
          </span>
        </div>
      </>
    );
  }
  const needsOnboarding =
    !loading && !error && (!data.me || data.me.onboardingVersion !== 2);
  const visible = (v: View) =>
    ((v !== "UNESCO Secretariat" && v !== "Dashboard") || data.admin) &&
    (v !== "Core Group workspace" || data.canAccessWorkspace === true) &&
    (v !== "Logo review" || canReviewLogo(access)) &&
    (v !== "Mailing lists" || data.admin || mailingAccess(access).length > 0) &&
    (v !== "Messages" || !!data.me) && (v !== "Chat moderation" || monitor) &&
    (v !== "Task boards" || (!!data.me && (boardBodies(access).length > 0 || myTasks.length > 0))) &&
    (v !== "Templates" || templatesAccess) && (v !== "Decade timeline" || !!data.me);
  const counts: Partial<Record<View, number>> = { Members: people.length, Opportunities: openOps.length, ...(pendingRoles + pendingApps.length ? { "UNESCO Secretariat": pendingRoles + pendingApps.length } : {}), ...(unreadChats ? { Messages: unreadChats } : {}), ...(openReports ? { "Chat moderation": openReports } : {}), ...(bellTasks.length ? { "Task boards": bellTasks.length } : {}) };
  const info = viewInfo(view);
  const wg = view === "Working Groups" && activeGroup ? groups[activeGroup - 1] : null;
  const bodyPage = view === "Governance" && activeBody ? bodySpace(activeBody) || null : null;
  const bodyRecord = bodyPage ? data.governance?.find((g: any) => g.id === bodyPage.id) : null;
  // Working documents: visible to leadership and Core Group roles of any body (data.canAccessWorkspace).
  const docs = data.canAccessWorkspace === true ? documentFolder(wg ? "wg" + wg.id : bodyPage?.folder || "") : undefined;
  const accent = wg?.color || bodyPage?.color;
  const firstName = (data.me?.name || "").split(" ")[0];
  const heroTitle = wg
    ? wg.title
    : bodyPage
      ? bodyPage.title
    : view === "Community"
      ? firstName ? "Welcome, " + firstName : "Welcome to DACS Community"
      : info.title;
  const heroText = wg ? wg.description : bodyPage ? bodyRecord?.description || bodyPage.description : info.description;
  const heroPhoto = wg ? groupPhotos[wg.id] : bodyPage ? bodyPage.photo : info.photo;
  const docsLink = docs && (
    <a className="btn docs-link" href={docs.href} target="_blank" rel="noopener noreferrer" title={"Opens the SharePoint folder “" + docs.folder + "” in a new tab"}>
      <FolderOpen size={16} />
      Working documents on SharePoint
      <ArrowUpRight size={14} />
    </a>
  );
  const following = (id: number) => data.follows.includes(id);
  function toggleFollow(id: number, message?: string) {
    if (requireProfile())
      mutate(
        { action: "follow", wg: id, follow: !following(id) },
        message || (following(id) ? "Group unfollowed." : "Following this Working Group."),
      );
  }
  const heroActions = (
    <>
      {view === "Community" && (
        <button className="btn primary" onClick={() => openModal("post")}>
          <Plus size={16} />
          Share an update
        </button>
      )}
      {view === "Opportunities" && (
        <button className="btn primary" onClick={() => openModal("opportunity")}>
          <Plus size={16} />
          Propose an activity
        </button>
      )}
      {view === "Members" && (
        <button className="btn primary" onClick={() => navigate("My profile")}>
          <UserRound size={16} />
          {data.me ? "Edit my profile" : "Create my profile"}
        </button>
      )}
      {wg && (
        <>
          <button className="btn" onClick={() => openGroup(null)}>
            <ArrowLeft size={16} />
            All Working Groups
          </button>
          {termsOfReference["wg" + wg.id] && <button className="btn" onClick={() => setTor("wg" + wg.id)}><ScrollText size={16} /> Terms of Reference</button>}
          {docsLink}
          <button className="btn primary" disabled={saving} onClick={() => toggleFollow(wg.id, "Follow preferences saved.")}>
            {following(wg.id) ? <Check size={16} /> : <Plus size={16} />}
            {following(wg.id) ? "Following" : "Follow group"}
          </button>
          {data.me && (broadStatus(wg.id) === "member"
            ? <span className="btn hero-standing" title="Confirmed by the UNESCO Secretariat"><BadgeCheck size={16} /> Broad Group member</span>
            : broadStatus(wg.id) === "pending"
              ? <span className="btn hero-standing pending" title="The UNESCO Secretariat reviews your application"><Clock size={16} /> Application sent</span>
              : <button className="btn" onClick={() => applyBroad(wg.id)}><UserPlus size={16} /> {broadStatus(wg.id) === "declined" ? "Apply again to the Broad Group" : "Apply to join the Broad Group"}</button>)}
        </>
      )}
      {bodyPage && (
        <>
          <button className="btn" onClick={() => openBody(null)}>
            <ArrowLeft size={16} />
            All governing bodies
          </button>
          {bodyPage.id !== "unesco" && canOrganise(access, bodyPage.id) && (
            <button className="btn" onClick={() => { navigate("Meeting polls"); setPollBody(bodyPage.id); }}>
              <CalendarClock size={16} />
              Plan a meeting
            </button>
          )}
          {termsOfReference[bodyPage.id] && <button className="btn" onClick={() => setTor(bodyPage.id)}><ScrollText size={16} /> Terms of Reference</button>}
          {bodyPage.id === "unesco" && data.admin && (
            <button className="btn" onClick={() => navigate("UNESCO Secretariat")}>
              <ShieldCheck size={16} />
              Manage UNESCO access
            </button>
          )}
          {docsLink}
        </>
      )}
    </>
  );
  // An account banned by the UNESCO Secretariat sees only this notice.
  if (data.banned)
    return (
      <div className="banned-page">
        <section className="banned-card">
          <img src={asset("/assets/decade-logo-color.webp")} alt="Decade of Action for Cryospheric Sciences 2025–2034" />
          <ShieldAlert size={30} />
          <h1>Your access to DACS Community is suspended</h1>
          <p>The UNESCO Secretariat has suspended this account. You cannot take part in the platform at the moment.</p>
          <p className="micro">If you think this is an error, contact the Decade Secretariat at UNESCO’s Intergovernmental Hydrological Programme.</p>
          <button type="button" className="btn" onClick={() => void signOutMember()}>Sign out</button>
        </section>
      </div>
    );
  return (
    <PeopleContext.Provider value={data.people || []}>
    <div className={"app-shell" + (view === "Logo review" ? " wide-view" : "")} inert={needsOnboarding}>
      <a className="skip-link" href="#main">Skip to main content</a>
      <div className="utility-bar">
        <div className="utility-inner">
          <span>United Nations Decade of Action for Cryospheric Sciences 2025–2034</span>
          <div className="utility-links">
            <a className="hide-sm" href={publicWebsite} target="_blank" rel="noopener noreferrer">
              <Globe size={13} />
              Official website
              <ArrowUpRight size={12} />
            </a>
            <span className="divider hide-sm" />
            <button type="button" onClick={toggleTheme}>
              {light ? <Moon size={13} /> : <Sun size={13} />}
              {light ? "Dark mode" : "Light mode"}
            </button>
          </div>
        </div>
      </div>
      <header className={"site-header" + (scrolled ? " scrolled" : "")}>
        <div className="header-inner">
          <button className="header-icon menu-trigger" aria-label="Open navigation" onClick={() => setNavOpen(true)}>
            <Menu size={22} />
          </button>
          <button className="header-brand" onClick={() => navigate("Community")} aria-label="DACS Community home">
            <img className="decade-logo logo-light" src={asset("/assets/decade-logo-color.webp")} alt="Decade of Action for Cryospheric Sciences 2025–2034" />
            <img className="decade-logo logo-dark" src={asset("/assets/decade-logo-white.webp")} alt="Decade of Action for Cryospheric Sciences 2025–2034" />
            <span className="brand-divider" />
            <img className="unesco-logo logo-light" src={asset("/assets/unesco-logo-color.webp")} alt="UNESCO" />
            <img className="unesco-logo logo-dark" src={asset("/assets/unesco-logo-white.webp")} alt="UNESCO" />
            <span className="brand-divider" />
            <span className="header-title">
              <strong>DACS Community</strong>
              <span>Member platform of the Decade</span>
            </span>
          </button>
          <div className="header-actions">
            {data.me?.onboardingVersion===2&&<MeetingNotifications tools={meetingTools} onPoll={id=>{navigate("Meeting polls");setPollFocus(id);}} onCreate={body=>{navigate("Meeting polls");setPollBody(body);}}
              mentions={inbox||[]} spaceLabel={spaceLabel} onMention={openMention}
              actions={myActions} onAction={a=>void openMeeting(a.eventId)}
              consultations={consultationTools.pending} onConsultation={openConsultation}
              messages={bellMessages} onMessage={(id) => { setChatTarget({ chatId: id }); navigate("Messages"); }} onReadMessages={(ids) => ids.forEach((id) => void markChatRead(id, myId).catch(() => {}))} updates={bellUpdates} tasks={bellTasks} onTask={() => { navigate("Task boards"); setTaskFocus("mine"); }}
              onReadAll={()=>{const ids=(inbox||[]).filter(i=>!i.read).map(i=>i.id);void markRead(uid,ids).catch(e=>toast.error(friendlyError(e)));}}/>}
            {signedIn && (
              <button
                className={"header-icon" + (refreshing ? " busy" : "")}
                onClick={refresh}
                disabled={loading || refreshing}
                aria-label="Refresh community data"
                title="Refresh. Data also updates every minute when you are not editing."
              >
                <RefreshCw size={18} />
              </button>
            )}
            {signedIn ? (
              <AccountMenu me={data.me} email={firebaseUser?.email || ""} light={light} toggleTheme={toggleTheme} navigate={navigate} onWelcome={() => setWelcome(true)} />
            ) : (
              <button className="btn primary" onClick={() => openSignIn()}>
                <LogIn size={15} />
                Sign in
              </button>
            )}
          </div>
        </div>
        <div className={"top-progress" + (loading || refreshing || saving ? " on" : "")} aria-hidden="true" />
      </header>
      <div className="layout">
        <aside className="side-panel" aria-label="Sections">
          <MeCard me={data.me} onOpen={() => navigate("My profile")} />
          <NavList view={view} navigate={navigate} visible={visible} counts={counts} />
        </aside>
        <main className="main-content" id="main">
          <section
            className={"page-hero has-photo" + (accent ? " has-accent" : "") + (view === "Logo review" ? " compact" : "")}
            style={accent ? ({ "--hero-accent": accent } as React.CSSProperties) : undefined}
          >
            <PhotoBackdrop key={heroPhoto.id} photo={heroPhoto} eager />
            <nav aria-label="Breadcrumb">
              <ol className="breadcrumb">
                <li>
                  {view === "Community" ? <span aria-current="page">Home</span> : <button onClick={() => navigate("Community")}>Home</button>}
                </li>
                {view !== "Community" && (
                  <li>
                    <ChevronRight size={13} />
                    {wg ? <button onClick={() => openGroup(null)}>{info.label}</button> : bodyPage ? <button onClick={() => openBody(null)}>{info.label}</button> : <span aria-current="page">{info.label}</span>}
                  </li>
                )}
                {bodyPage && (
                  <li>
                    <ChevronRight size={13} />
                    <span aria-current="page">{bodyPage.short}</span>
                  </li>
                )}
                {wg && (
                  <li>
                    <ChevronRight size={13} />
                    <span aria-current="page">WG{wg.id} · {wg.short}</span>
                  </li>
                )}
              </ol>
            </nav>
            <div className="page-hero-row" key={view + String(activeGroup) + (activeBody || "")}>
              <div className="hero-title-row">
                {wg && <span className="hero-wg-badge" aria-hidden="true">WG{wg.id}</span>}
                <div>
                  {view === "Community" && <div className="eyebrow">DACS Community</div>}
                  <h1>{heroTitle}</h1>
                  {heroText && <p>{heroText}</p>}
                </div>
              </div>
              <div className="page-hero-actions">{heroActions}</div>
            </div>
          </section>
          {error && (
            <div className="error-banner" role="alert">
              {error}{" "}
              <button className="text-button" onClick={() => load()}>
                Try again
              </button>
            </div>
          )}
          {data.more && Object.values(data.more).some(Boolean) && (
            <div className="notice">
              <span>Showing loaded records. Search applies to this batch.</span>
            </div>
          )}
          {loading ? (
            <>
              <span className="sr-only" role="status">Loading…</span>
              <SkeletonPage />
            </>
          ) : (
          <div className="page-body" key={view + String(activeGroup) + (activeBody || "")}>
        {view === "Community" && (
          <>
            <DecadeIntro />
            {!data.me && (
              <section className="glass welcome">
                <div className="welcome-row">
                  <div>
                    <div className="eyebrow">
                      Your contribution starts here
                    </div>
                    <h2>A profile that connects you to action.</h2>
                    <p>
                      Record your interests, skills and availability.
                      Working Groups can then find expertise for the
                      activities they are developing.
                    </p>
                    <button
                      className="btn primary"
                      onClick={() => navigate("My profile")}
                    >
                      Create your member profile
                    </button>
                  </div>
                  <Snowflake className="welcome-symbol" size={90} />
                </div>
              </section>
            )}
            <section className="stats" aria-label="Community overview">
              <StatTile value={people.length} label="Members" Icon={Users} accent="#0a6eb4" onClick={() => navigate("Members")} />
              <StatTile value={openOps.length} label="Open activities" Icon={Briefcase} accent="#00a3c4" onClick={() => navigate("Opportunities")} />
              <StatTile value={myContributions.length} label="My contributions" Icon={FileCheck} accent="#599c41" onClick={() => navigate("My contributions")} />
            </section>
            <div className="cols">
              <div className="stack">
                <section>
                  <div className="section-title">
                    <h2>Open to contributions</h2>
                    <button
                      className="text-button arrow"
                      onClick={() => navigate("Opportunities")}
                    >
                      View all activities <ArrowRight size={14} />
                    </button>
                  </div>
                  <div className="op-grid">
                    {openOps.slice(0, 2).map(opCard)}
                    {!openOps.length && (
                      <div className="glass">
                        <Empty
                          icon={Briefcase}
                          title="Activities will appear here"
                          text="Propose the first activity."
                        />
                      </div>
                    )}
                  </div>
                </section>
                <section>
                  <div className="section-title">
                    <h2>Community activity</h2>
                    <span className="micro">
                      Updates from across the Decade
                    </span>
                  </div>
                  <div className="glass post-compose">
                    <Avatar
                      name={data.me?.name || "You"}
                      uid={data.me?.id}
                      hasPhoto={data.me?.hasPhoto}
                      version={data.me?.updatedAt}
                    />
                    <button onClick={() => openModal("post")}>
                      Share a contribution, question or update…
                    </button>
                  </div>
                  <div className="feed-controls">
                    <Tabs
                      value={feedMode}
                      onValueChange={setFeedMode}
                      className="tabs-surface"
                    >
                      <TabsList>
                        <TabsTrigger value="all">All updates</TabsTrigger>
                        <TabsTrigger value="following">Following</TabsTrigger>
                      </TabsList>
                    </Tabs>
                    <Pick
                      label="Filter feed by Working Group"
                      value={wgFilter}
                      onChange={setWgFilter}
                      items={[
                        { value: "all", label: "All groups" },
                        ...groups.map((g) => ({
                          value: String(g.id),
                          label: "WG" + g.id + " · " + g.short,
                        })),
                      ]}
                    />
                  </div>
                  <div className="stack" style={{ gap: 14 }}>
                    {realPosts.map(postCard)}
                    {!realPosts.length && (
                      <div className="glass">
                        <Empty
                          icon={Newspaper}
                          title="No updates yet"
                          text={
                            feedMode === "following"
                              ? "Follow a group to see its updates."
                              : "Share the first update."
                          }
                        />
                      </div>
                    )}
                  </div>
                </section>
              </div>
              <aside>
                {myActions.some((a) => a.status === "open") && <MyActions actions={myActions} onOpenMeeting={(id) => void openMeeting(id)} />}
                <section className="glass panel">
                  <div className="section-title">
                    <h2>Upcoming events</h2>
                    <button className="text-button arrow" onClick={() => navigate("Calendar")}>
                      Calendar <ArrowRight size={14} />
                    </button>
                  </div>
                  {upcoming.length ? (
                    <div className="upcoming-list">
                      {upcoming.map((e: CalendarEvent) => {
                        const start = new Date(e.startAt);
                        return (
                          <button
                            className="upcoming-item"
                            key={e.id}
                            onClick={() => {
                              navigate("Calendar");
                              setCalendarFocus(e);
                            }}
                          >
                            <span className="date-block" aria-hidden="true">
                              <b>{start.toLocaleDateString("en-GB", { day: "numeric" })}</b>
                              <small>{start.toLocaleDateString("en-GB", { month: "short" })}</small>
                            </span>
                            <div>
                              <strong>{e.title}</strong>
                              <span>
                                {start.toLocaleDateString("en-GB", { weekday: "short" })}{" "}
                                {start.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", timeZoneName: "short" })}
                                {e.body ? " · " + bodyLabel(e.body) : e.location ? " · " + e.location : ""}
                              </span>
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  ) : (
                    <p className="micro">No upcoming events in the calendar.</p>
                  )}
                </section>
                <section className="glass panel">
                  <div className="section-title">
                    <h2>Working Groups</h2>
                    <button className="text-button arrow" onClick={() => navigate("Working Groups")}>
                      All <ArrowRight size={14} />
                    </button>
                  </div>
                  {groups.map((g) => (
                    <div className="group-row" key={g.id}>
                      <span
                        className="group-number"
                        style={{ "--wg-color": g.color } as any}
                      >
                        WG{g.id}
                      </span>
                      <div>
                        <h3>{g.short}</h3>
                        {following(g.id) && <span className="following-chip"><Check size={12} />Following</span>}
                      </div>
                      <button
                        className={"btn small icon follow" + (following(g.id) ? " on" : "")}
                        disabled={saving}
                        aria-label={
                          (following(g.id)
                            ? "Unfollow "
                            : "Follow ") +
                          "WG" +
                          g.id
                        }
                        title={following(g.id) ? "Unfollow" : "Follow"}
                        onClick={() => toggleFollow(g.id)}
                      >
                        {following(g.id) ? (
                          <Check size={14} />
                        ) : (
                          <Plus size={14} />
                        )}
                      </button>
                    </div>
                  ))}
                </section>
                <section className="glass panel">
                  <div className="section-title">
                    <h2>Meet the community</h2>
                    <button className="text-button arrow" onClick={() => navigate("Members")}>
                      Members <ArrowRight size={14} />
                    </button>
                  </div>
                  {people.slice(0, 3).map((p) => (
                    <button
                      key={p.id}
                      onClick={() => setSelected(p)}
                      className="group-row"
                    >
                      <Avatar
                        name={p.name}
                        uid={p.id}
                        hasPhoto={p.hasPhoto}
                        version={p.updatedAt}
                      />
                      <div>
                        <h3>{p.name}</h3>
                        {p.country && <p style={{ marginBottom: 6 }}>{p.country}</p>}
                        <MemberBadges badges={p.membershipBadges} compact />
                      </div>
                    </button>
                  ))}
                </section>
              </aside>
            </div>
          </>
        )}
        {view === "Members" && (
          <>
            <div className="view-tabs" role="tablist" aria-label="Directory display">
              <button role="tab" aria-selected={memberMode === "list"} className={memberMode === "list" ? "on" : ""} onClick={() => setMemberMode("list")}><Users size={16} /> Directory</button>
              <button role="tab" aria-selected={memberMode === "map"} className={memberMode === "map" ? "on" : ""} onClick={() => setMemberMode("map")}><Globe size={16} /> Map</button>
            </div>
            {memberMode === "map" ? (
              <section className="glass dash-card"><MembersMap people={people} categories={categories} genderTotals={memberStats} focusCountry={selected?.country} onOpenProfile={setSelected} genderOf={data.admin ? (id: string) => people.find((p) => p.id === id)?.gender || "" : undefined} note="Members visible in the directory, by the country in their profile." /></section>
            ) : <>
            {filters()}
            <div className="member-grid">
              {filtered.map(memberCard)}
            </div>
            {!filtered.length && (
              <div className="glass">
                <Empty
                  icon={Search}
                  title="No matching profiles"
                  text="Try a different skill, Working Group or region."
                />
              </div>
            )}
            </>}
          </>
        )}
        {view === "Opportunities" && (
          <>
            <div className="filter-bar">
              <div className="toolbar">
                <Pick
                  label="Working Group"
                  value={wgFilter}
                  onChange={setWgFilter}
                  items={[
                    { value: "all", label: "All Working Groups" },
                    ...groups.map((g) => ({
                      value: String(g.id),
                      label: "WG" + g.id + " · " + g.short,
                    })),
                  ]}
                />
                <span className="micro">
                  Broad members can propose activities. Working Group managers
                  review and publish them.
                </span>
              </div>
            </div>
            <div className="op-grid">
              {ops
                .filter((o) => wgFilter === "all" || activityGroups(o).includes(Number(wgFilter)))
                .map(opCard)}
            </div>
            {!ops.length && (
              <div className="glass">
                <Empty
                  icon={Briefcase}
                  title="No activities published yet"
                  text="Propose a task, scientific review, case study or communication activity."
                />
              </div>
            )}
          </>
        )}
        {view === "Working Groups" &&
          (activeGroup ? (
            <WorkingGroupPage
              wg={activeGroup}
              tab={wgTab}
              onTab={setWgTab}
              items={workItems || []}
              activities={ops.filter((o) => activityGroups(o).includes(Number(activeGroup)))}
              members={people.filter((p) => groupStanding(p, activeGroup) === "core")}
              broadMembers={people.filter((p) => groupStanding(p, activeGroup) === "broad")}
              interested={people.filter((p) => groupStanding(p, activeGroup) === "interested")}
              broadStatus={data.me ? broadStatus(activeGroup) : "none"}
              onApply={() => applyBroad(activeGroup)}
              leads={!!data.me && leadsActive}
              pendingRequests={groupApps.filter((a) => a.status === "pending").length}
              requests={<GroupRequests body={"wg" + activeGroup} applications={groupApps} people={people} onOpenProfile={setSelected} onDecided={() => void refresh()} />}
              events={(data.events || []).filter((event: CalendarEvent) => event.body === "wg" + activeGroup || event.ocs.includes(Number(activeGroup)))}
              posts={data.posts.filter((p: any) => p.wg === activeGroup || linkedGroups(p.mgs).includes(Number(activeGroup)))}
              core={!!data.me && bodyLevel(access, "wg" + activeGroup) >= 2}
              signedIn={!!data.me}
              appointments={<GovernanceSeats body={{ id: "wg" + activeGroup, ...(data.governance?.find((g: any) => g.id === "wg" + activeGroup) || {}) }} people={data.people} onOpenProfile={setSelected} />}
              tor={<TorCard body={"wg" + activeGroup} onOpen={() => setTor("wg" + activeGroup)} />}
              discussion={<GroupDiscussion
                space={"wg" + activeGroup}
                label={spaceLabel("wg" + activeGroup)}
                me={data.me}
                people={people}
                moderator={access.admin || bodyLevel(access, "wg" + activeGroup) >= 3}
                focusId={discussionFocus}
                onFocused={() => setDiscussionFocus(undefined)}
                onCreateProfile={() => navigate("My profile")}
                fileBody={shareBody(access, "wg" + activeGroup)}
              />}
              taskBoard={<TaskBoard body={"wg" + activeGroup} access={access} people={data.people || []} governance={data.governance || []} compact />}
              opCard={opCard}
              memberCard={memberCard}
              eventCard={eventCard}
              postCard={postCard}
              onOpenActivity={setOpDetail}
              onOpenEvent={(event: CalendarEvent) => { navigate("Calendar"); setCalendarFocus(event); }}
              onPropose={() => { setOpDraft((d: any) => ({ ...d, wg: activeGroup, mgs: d.mgs.length ? d.mgs : [activeGroup + ".1"] })); openModal("opportunity"); }}
            />
          ) : (
            <div className="group-cards">
              {groups.map((g, i) => {
                const Icon = icons[i];
                return (
                  <section
                    className="glass group-card clickable-card"
                    key={g.id}
                    style={{ "--wg-color": g.color, "--wg-ink": g.ink } as any}
                  >
                    <div className="group-card-band has-photo">
                      <PhotoBackdrop photo={groupPhotos[g.id]} sizes="(max-width: 800px) 100vw, 600px" />
                      <span className="wg-label">
                        <small>Working Group</small>
                        <span className="big-number">0{g.id}</span>
                      </span>
                      <span className="group-card-icon"><Icon size={24} /></span>
                    </div>
                    <h2>{g.title}</h2>
                    <p>{g.description}</p>
                    <div className="tags">
                      {g.skills.map((s) => (
                        <span className="tag" key={s}>
                          {s}
                        </span>
                      ))}
                    </div>
                    <div className="card-footer">
                      <span>
                        <Users size={14} />
                        {people.filter((p) => p.wgs?.includes(g.id)).length}{" "}
                        interested profiles
                        {following(g.id) && <span className="following-chip" style={{ marginLeft: 8 }}><Check size={12} />Following</span>}
                      </span>
                      <button
                        className="text-button arrow stretch"
                        onClick={() => openGroup(g.id)}
                        aria-label={"Open the space of WG" + g.id + " · " + g.short}
                      >
                        Open group space <ArrowRight size={14} />
                      </button>
                    </div>
                  </section>
                );
              })}
            </div>
          ))}
        {view === "Find expertise" && (
          <>
            <section className="glass panel">
              <div className="section-title">
                <h2>Select an activity</h2>
                <span className="pill blue">Explainable matching</span>
              </div>
              {ops.length ? (
                <Pick
                  label="Activity to match"
                  value={selectedOp?.id || ""}
                  onChange={setMatchOp}
                  className="op-picker"
                  items={ops.map((o) => ({
                    value: o.id,
                    label: "WG" + o.wg + " · " + o.title,
                  }))}
                />
              ) : (
                <p>Publish an activity to search for matching contributors.</p>
              )}
              {selectedOp && (
                <>
                  <div className="tags" style={{ marginTop: 15 }}>
                    {selectedOp.skills.map((s: string) => (
                      <span className="tag" key={s}>
                        {s}
                      </span>
                    ))}
                  </div>
                  <details className="micro match-method" style={{ marginTop: 14 }}>
                    <summary>How matching works</summary>
                    <p>
                      Skills 60% · WG interest 20% · region 10% · language 10%.
                      Confirm availability with the member.
                    </p>
                  </details>
                </>
              )}
            </section>
            {filters(true)}
            <section className="glass panel">
              {matched.map((p) => (
                <div className="match-row" key={p.id}>
                  <Avatar
                    name={p.name}
                    uid={p.id}
                    hasPhoto={p.hasPhoto}
                    version={p.updatedAt}
                  />
                  <div className="match-info">
                    <h3>{p.name}</h3>
                    {p.headline && <p>{p.headline}</p>}
                    <MemberBadges badges={p.membershipBadges} compact />
                    <div className="tags">
                      {p.match.shared.map((s: string) => (
                        <span key={s} className="tag">
                          ✓ {s}
                        </span>
                      ))}
                      {p.match.wg && <span className="tag">WG interest</span>}
                      {p.match.region && (
                        <span className="tag">Regional scope</span>
                      )}
                      {p.match.language && (
                        <span className="tag">{selectedOp.language}</span>
                      )}
                    </div>
                    <p className="location">
                      <Clock size={13} />
                      {p.availability}
                    </p>
                    <button
                      className="text-button arrow"
                      onClick={() => setSelected(p)}
                    >
                      View profile <ArrowRight size={14} />
                    </button>
                  </div>
                  <div className="score-ring" style={{ "--p": p.match.score } as any} aria-label={p.match.score + "% profile match"} title="Profile match">
                    <b>{p.match.score}%</b>
                  </div>
                </div>
              ))}
              {!matched.length && (
                <Empty
                  icon={Search}
                  title="No matching contributors"
                  text="Try another filter."
                />
              )}
            </section>
          </>
        )}
        {view === "My contributions" && (
          <>
            <div className="stats" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))" }}>
              {["Interested", "Shortlisted", "In progress", "Completed"].map(
                (status, i) => (
                  <StatTile
                    key={status}
                    value={myContributions.filter((c: any) => c.status === status).length}
                    label={status}
                    Icon={[Bookmark, BadgeCheck, Hourglass, Check][i]}
                    accent={["#0a6eb4", "#00a3c4", "#c27c0e", "#599c41"][i]}
                  />
                ),
              )}
            </div>
            <section className="glass panel">
              <div className="section-title">
                <h2>Your activity record</h2>
                <button
                  className="text-button arrow"
                  onClick={() => navigate("Opportunities")}
                >
                  Find an activity <ArrowRight size={14} />
                </button>
              </div>
              {myContributions.map((c: any) => (
                  <div className="contribution-row" key={c.id}>
                    <div
                      className="row"
                      style={{ justifyContent: "space-between" }}
                    >
                      <WgPill wg={c.wg} />
                      <span className="pill blue">{c.status}</span>
                    </div>
                    <h3>{c.opportunity_title}</h3>
                    <p>{c.message}</p>
                    <div
                      className="row"
                      style={{ justifyContent: "space-between" }}
                    >
                      <span className="history">
                        Interest recorded {date(c.createdAt)}
                      </span>
                      {!["Completed", "Withdrawn", "Not selected"].includes(
                        c.status,
                      ) && (
                        <button
                          className="text-button danger"
                          disabled={saving}
                          onClick={() =>
                            mutate(
                              {
                                action: "contributionStatus",
                                id: c.id,
                                status: "Withdrawn",
                              },
                              "Interest withdrawn.",
                            )
                          }
                        >
                          Withdraw interest
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              {!myContributions.length && (
                <Empty
                  icon={FileCheck}
                  title="Your contributions start here"
                  text="Record interest in an open activity. The Working Group can review your proposal and track agreed work."
                />
              )}
            </section>
            {(data.admin || !!data.me?.managedWgs?.length) && (
              <section className="glass panel">
                <div className="section-title">
                  <h2>Working Group review</h2>
                  <span className="pill">Management access</span>
                </div>
                {data.contributions
                  .filter((c: any) => eligible(c.wg))
                  .map((c: any) => (
                    <div className="contribution-row" key={c.id}>
                      <WgPill wg={c.wg} />
                      <h3>
                        {c.member_name} · {c.opportunity_title}
                      </h3>
                      <p>{c.message}</p>
                      <Pick
                        label="Contribution status"
                        value={c.status}
                        onChange={(v) =>
                          mutate(
                            {
                              action: "contributionStatus",
                              id: c.id,
                              status: v,
                            },
                            "Contribution status saved.",
                          )
                        }
                        items={opts([
                          "Interested",
                          "Shortlisted",
                          "Selected",
                          "In progress",
                          "Completed",
                          "Not selected",
                        ])}
                      />
                    </div>
                  ))}
                {data.opportunities
                  .filter((o: any) => eligible(o.wg) && o.status === "pending")
                  .map((o: any) => (
                    <div className="contribution-row" key={o.id}>
                      <span className="pill amber" style={{ justifySelf: "start" }}>Awaiting review</span>
                      <h3>{o.title}</h3>
                      <p>{o.description}</p>
                      <button
                        className="btn primary"
                        style={{ justifySelf: "start" }}
                        disabled={saving}
                        onClick={() =>
                          mutate(
                            {
                              action: "opportunityStatus",
                              id: o.id,
                              status: "open",
                            },
                            "Activity published.",
                          )
                        }
                      >
                        Approve & publish
                      </button>
                    </div>
                  ))}
              </section>
            )}
          </>
        )}
        {view === "My profile" && (
          <section className="glass panel">
            {data.me && (
              <div className="profile-card-head">
                <div className="member-head">
                  <Avatar name={data.me.name} uid={data.me.id} hasPhoto={data.me.hasPhoto} version={data.me.updatedAt} large />
                  <div>
                    <h2 style={{ fontSize: 22 }}>{data.me.name}</h2>
                    {data.me.headline && <p>{data.me.headline}</p>}
                  </div>
                </div>
                <MemberBadges badges={data.me?.membershipBadges} />
                <ProfileCrystal me={data.me} />
              </div>
            )}
            <ProfileEditor
              key={data.me?.updatedAt || "new"}
              initial={data.me}
              categories={categories}
              saving={saving}
              onSave={async (profile) => {
                const ok = await mutate(
                  { action: "profile", profile },
                  "Your profile has been saved.",
                );
                if (ok) navigate("Members");
                return ok;
              }}
            />
          </section>
        )}
        {view === "Official Decade website" && <OfficialWebsite />}
        {view === "Calendar" && signedIn && <DecadeCalendar people={people} uid={firebaseUser?.uid || ""} admin={access.admin} canAdd={!!data.me} focusEvent={calendarFocus} access={access} meetingSeed={meetingSeed} onOpenPolls={()=>navigate("Meeting polls")} onSaved={()=>{void load(true);}} />}
        {view === "News" && data.me && <NewsBoard uid={firebaseUser?.uid||""} name={data.me.name} admin={access.admin} access={access}/>}
        {view === "Meeting polls" && data.me && (
          <>
            <div className="view-tabs" role="tablist" aria-label="Polls and consultations">
              <button role="tab" aria-selected={pollTab === "polls"} className={pollTab === "polls" ? "on" : ""} onClick={() => setPollTab("polls")}><CalendarClock size={16} /> Scheduling polls{meetingTools.pending.length > 0 && <span className="nav-count">{meetingTools.pending.length}</span>}</button>
              <button role="tab" aria-selected={pollTab === "consultations"} className={pollTab === "consultations" ? "on" : ""} onClick={() => setPollTab("consultations")}><ListChecks size={16} /> Consultations{consultationTools.pending.length > 0 && <span className="nav-count">{consultationTools.pending.length}</span>}</button>
            </div>
            {pollTab === "polls"
              ? <MeetingHub access={access} tools={meetingTools} focusId={pollFocus} createBody={pollBody} onSchedule={seed=>{navigate("Calendar");setMeetingSeed(seed);}}/>
              : <Consultations access={access} tools={consultationTools} focusId={consultationFocus} />}
          </>
        )}
        {view === "Work plans" && data.me && <FlagshipOverview items={workItems} error={workError} activities={ops} canEdit={(n) => bodyLevel(access, "wg" + n) >= 2} onOpenGroup={(n) => { navigate("Working Groups"); setActiveGroup(n); setWgTab("projects"); }} onOpenActivity={setOpDetail} />}
        {view === "Decision register" && data.me && <DecisionRegister access={access} events={data.events || []} onOpenMeeting={(id) => void openMeeting(id)} />}
        {view === "Dashboard" && data.admin && <SecretariatDashboard data={data} categories={categories} onOpenPending={() => navigate("Opportunities")} onOpenLogo={() => navigate("Logo review")} />}
        {view === "Logo review" && canReviewLogo(access) && <LogoReview access={access} light={light}/>}
        {view === "Core Group workspace" && data.canAccessWorkspace && <CoreWorkspace />}
        {view === "Governance" && (bodyPage ? (
          <section className="glass group-detail body-detail" style={{ "--wg-color": bodyPage.color } as any}>
            <TorCard body={bodyPage.id} onOpen={() => setTor(bodyPage.id)} />
            <div className="subsection-title">{bodyPage.id === "unesco" ? "Secretariat members" : "Appointments"}</div>
            {bodyPage.id === "unesco"
              ? <UnescoMembers people={people} onOpenProfile={setSelected} />
              : <GovernanceSeats body={{ ...emptyBody, ...(bodyRecord || {}), id: bodyPage.id }} people={data.people} onOpenProfile={setSelected} />}
            {bodyPage.id !== "unesco" && (() => {
              const meetings = (data.events || [])
                .filter((e: CalendarEvent) => e.body === bodyPage.id && Date.parse(e.endAt) >= Date.now())
                .sort((a: CalendarEvent, b: CalendarEvent) => Date.parse(a.startAt) - Date.parse(b.startAt));
              const news = data.posts.filter((p: any) => p.bodyId === bodyPage.id);
              return <>
                <div className="subsection-title">Upcoming meetings</div>
                {meetings.length
                  ? <div className="op-grid">{meetings.map(eventCard)}</div>
                  : <p className="micro">No upcoming {bodyPage.short} meeting is listed in the calendar you can see.</p>}
                {news.length > 0 && <><div className="subsection-title">News</div><div className="stack" style={{ gap: 14 }}>{news.map(postCard)}</div></>}
              </>;
            })()}
            {bodyPage.id !== "unesco" && data.me && bodyLevel(access, bodyPage.id) >= 2 && <TaskBoard body={bodyPage.id} access={access} people={data.people || []} governance={data.governance || []} compact />}
            {["smc", "esc"].includes(bodyPage.id) && data.me && (
              <DecisionRegister compact only={bodyPage.id} access={access} events={data.events || []} onOpenMeeting={(id) => void openMeeting(id)} onOpenRegister={() => navigate("Decision register")} />
            )}
            {!data.canAccessWorkspace && bodyPage.folder && (
              <p className="micro body-docs-note">Working documents on SharePoint are listed here for leadership and Core Group members of the Decade bodies.</p>
            )}
          </section>
        ) : (
          <GovernanceDirectory data={data} mutate={mutate} saving={saving}
            onManageUnesco={() => navigate("UNESCO Secretariat")} onOpenSpace={openSpace} onOpenProfile={setSelected} />
        ))}
        {view === "Messages" && data.me && <Messages me={data.me} people={data.people || []} chats={chats} target={chatTarget} onTargetUsed={() => setChatTarget(null)} onOpenProfile={setSelected} />}
        {view === "Chat moderation" && monitor && <ChatMonitor people={data.people || []} reports={reports} monitors={monitors} owner={chatOwner} meId={myId} />}
        {view === "Templates" && templatesAccess && <Templates />}
        {view === "Decade timeline" && data.me && <DecadeTimeline access={access} events={data.events || []} onOpenEvent={(id) => void openMeeting(id)} onOpenDecisions={() => navigate("Decision register")} />}
        {view === "Task boards" && data.me && <TaskBoards access={access} people={data.people || []} governance={data.governance || []} myTasks={myTasks} focus={taskFocus} />}
        {view === "Mailing lists" && data.me && <MailingLists access={access} email={data.user?.email || ""} people={data.people || []} />}
        {view === "UNESCO Secretariat" && data.admin && <RoleRequestsPanel data={data} mutate={mutate} saving={saving} onOpenProfile={setSelected} applications={pendingApps} onDecided={() => void refresh()} />}
        {view === "UNESCO Secretariat" && data.admin && (
          <SecretariatPanel
            data={data}
            categories={categories}
            mutate={mutate}
            saving={saving}
          />
        )}
          </div>
          )}
        </main>
      </div>
      <footer className="site-footer">
        <div className="footer-inner">
          <div className="footer-brand">
            <div className="footer-logos">
              <img src={asset("/assets/decade-logo-white.webp")} alt="Decade of Action for Cryospheric Sciences 2025–2034" />
              <i aria-hidden="true" />
              <img src={asset("/assets/unesco-logo-white.webp")} alt="UNESCO" />
            </div>
            <p>
              DACS Community connects the people contributing to the United Nations Decade of Action for
              Cryospheric Sciences 2025-2034. The Decade Secretariat is hosted by UNESCO’s
              Intergovernmental Hydrological Programme.
            </p>
          </div>
          <div className="footer-col">
            <h2>Platform</h2>
            <ul>
              {(["Members", "Working Groups", "Opportunities", "Calendar", "News"] as View[]).map((v) => (
                <li key={v}><button onClick={() => navigate(v)}>{viewInfo(v).label}</button></li>
              ))}
            </ul>
          </div>
          <div className="footer-col">
            <h2>The Decade</h2>
            <ul>
              <li><a href={publicWebsite} target="_blank" rel="noopener noreferrer">Official website <ArrowUpRight size={12} /></a></li>
              <li><a href={shareContentUrl} target="_blank" rel="noopener noreferrer">Publish your content <ArrowUpRight size={12} /></a></li>
              <li><a href={logoApplicationUrl} target="_blank" rel="noopener noreferrer">Apply to carry the logo <ArrowUpRight size={12} /></a></li>
              <li><button onClick={() => navigate("Governance")}>Governance</button></li>
            </ul>
          </div>
          <div className="footer-col">
            <h2>UNESCO</h2>
            <ul>
              <li><a href="https://www.unesco.org/en/ihp" target="_blank" rel="noopener noreferrer">Intergovernmental Hydrological Programme <ArrowUpRight size={12} /></a></li>
            </ul>
          </div>
        </div>
        <div className="footer-bottom">
          <div>
            <span>Decade of Action for Cryospheric Sciences 2025–2034</span>
            <span>DACS Community · member platform</span>
          </div>
        </div>
      </footer>
      <button
        className={"to-top" + (showTop ? " show" : "")}
        onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
        aria-label="Back to top"
        tabIndex={showTop ? 0 : -1}
      >
        <ArrowUp size={18} />
      </button>
    </div>
      <Sheet open={navOpen} onOpenChange={setNavOpen}>
        <SheetContent side="left" className="mobile-nav-sheet">
          <SheetTitle className="sr-only">Navigation</SheetTitle>
          <SheetDescription className="sr-only">Sections of DACS Community</SheetDescription>
          <div className="mobile-nav-head">
            <img src={asset("/assets/decade-logo-white.webp")} alt="Decade of Action for Cryospheric Sciences 2025–2034" />
          </div>
          <MeCard me={data.me} onOpen={() => navigate("My profile")} />
          <NavList view={view} navigate={navigate} visible={visible} counts={counts} />
        </SheetContent>
      </Sheet>
      <Dialog open={needsOnboarding}>
        <DialogContent
          className="detail-content onboarding-dialog"
          showCloseButton={false}
          onEscapeKeyDown={(e) => e.preventDefault()}
          onPointerDownOutside={(e) => e.preventDefault()}
          onInteractOutside={(e) => e.preventDefault()}
        >
          <DialogTitle>Welcome to DACS Community</DialogTitle>
          <DialogDescription>
            Tell us about your expertise and interests to complete your first
            member profile.
          </DialogDescription>
          <ProfileEditor
            key={firebaseUser?.uid}
            initial={data.me}
            categories={categories}
            saving={saving}
            onboarding
            onSave={(profile) =>
              mutate(
                { action: "profile", profile },
                "Welcome. Your member profile is ready.",
              )
            }
          />
          <AccountControls />
        </DialogContent>
      </Dialog>
      <Dialog open={!!meetingNudge} onOpenChange={(v) => !v && setMeetingNudge(null)}>
        <DialogContent className="detail-content meeting-nudge">
          <div className="nudge-icon" aria-hidden="true"><CalendarClock size={26} /></div>
          <DialogTitle>Time to plan your next meeting</DialogTitle>
          <DialogDescription>
            {meetingNudge?.length === 1 ? "Your group has" : "Your groups have"} not met for three weeks or more, and no meeting or poll is planned.
            Propose a few times with a scheduling poll and share its link with the group.
          </DialogDescription>
          <div className="nudge-list">
            {meetingNudge?.map((r: any) => (
              <div className={"nudge-item" + (r.reminder.urgent ? " urgent" : "")} key={r.id}>
                <div>
                  <strong>{/^wg[1-5]$/.test(r.id) ? spaceLabel(r.id) : bodyLabel(r.id)}</strong>
                  <span>{r.reminder.days} days since {r.events.some((e: any) => Date.parse(e.endAt) <= Date.now()) ? "the last meeting" : "meeting reminders started"} · {new Date(r.reminder.last).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" })}</span>
                </div>
                <button className="btn primary" onClick={() => { setMeetingNudge(null); navigate("Meeting polls"); setPollBody(r.id); }}>
                  <Plus size={16} /> Create a scheduling poll
                </button>
              </div>
            ))}
          </div>
          <div className="nudge-foot">
            <button className="text-button" onClick={() => setMeetingNudge(null)}>Remind me at my next sign-in</button>
          </div>
        </DialogContent>
      </Dialog>
      <WelcomeVideo open={welcome} onClose={closeWelcome} name={data.me?.name} />
      {celebrate && data.me && !welcome && !needsOnboarding && (
        <ApprovalCelebration person={data.me} app={celebrate}
          onClose={() => { markCelebrated(myId, [celebrate.id]); setCelebrate(null); }}
          onOpenGroup={(n) => openGroupTab(n, "overview")} />
      )}
      <TorDialog body={tor} onClose={() => setTor(null)} />
      <Dialog open={!!selected} onOpenChange={(v) => !v && setSelected(null)}>
        <DialogContent className={"detail-content event-sheet member-sheet ev" + (selected && lanyardSpace ? " with-lanyard" : "")} style={selected ? memberStyle(selected) : undefined}
          onPointerDownOutside={(e) => { if ((e.target as Element | null)?.closest?.(".member-lanyard")) e.preventDefault(); }}
          onInteractOutside={(e) => { if ((e.target as Element | null)?.closest?.(".member-lanyard")) e.preventDefault(); }}>
          {selected && lanyardSpace && <MemberLanyard person={selected} accent={memberAccent(selected)} />}
          {selected ? (
            <MemberSheet person={selected} contributions={data.contributions || []}
              canMessage={!!data.me && selected.id !== data.me.id}
              onMessage={() => openChat(selected)} onClose={() => setSelected(null)} />
          ) : (
            <><DialogTitle className="sr-only">Member profile</DialogTitle><DialogDescription className="sr-only">Member profile</DialogDescription></>
          )}
        </DialogContent>
      </Dialog>
      <ActivityDetail
        op={opDetail && !modal ? opDetail : null}
        onClose={() => setOpDetail(null)}
        people={data.people || []}
        me={data.me}
        projects={opDetail && eligible(opDetail.wg) ? (workItems || []).filter((i) => i.kind === "deliverable" && i.body === "wg" + opDetail.wg) : []}
        projectTitle={opDetail ? projectTitle(opDetail.project) : ""}
        match={opDetail && data.me ? match(data.me, opDetail) : null}
        applied={!!opDetail && data.contributions.some((c: any) => c.opportunity_id === opDetail.id && c.member_id === data.me?.id)}
        canManage={!!opDetail && !!eligible(opDetail.wg)}
        canEdit={!!opDetail && (!!data.admin || (!!data.me && opDetail.owner === data.me.id))}
        onApply={() => openModal("apply")}
        onFind={() => { setMatchOp(opDetail.id); setOpDetail(null); navigate("Find expertise"); }}
        onToggleStatus={async () => { if (await mutate({ action: "opportunityStatus", id: opDetail.id, status: opDetail.status === "open" ? "closed" : "open" }, "Activity status saved.")) setOpDetail(null); }}
        onEdit={() => {
          setEditingOp(opDetail.id);
          setOpDraft({ title: opDetail.title, description: opDetail.description, wg: opDetail.wg, skills: opDetail.skills || [], region: opDetail.region, language: opDetail.language, commitment: opDetail.commitment, deadline: opDetail.deadline || "", type: opDetail.type, mgs: opDetail.mgs || [], attachments: opDetail.attachments || [], project: opDetail.project || "" });
          setModal("opportunity");
        }}
        onDelete={async () => {
          if (!window.confirm(`Delete the activity “${opDetail.title}”? This cannot be undone.`)) return;
          if (await mutate({ action: "opportunityDelete", id: opDetail.id }, "Activity deleted.")) setOpDetail(null);
        }}
        onLink={async (project) => {
          try { await linkActivity(opDetail.id, project); setOpDetail({ ...opDetail, project }); toast.success(project ? "Activity linked to the flagship project." : "Link removed."); void refresh(); }
          catch (err) { toast.error(friendlyError(err)); }
        }}
      />
      <Dialog open={!!modal} onOpenChange={(v) => { if (!v) { setModal(null); if (editingOp) { setEditingOp(null); setOpDraft(blankActivity); } } }}>
        <DialogContent className="detail-content">
          <DialogTitle>
            {modal === "post"
              ? "Share a community update"
              : modal === "opportunity"
                ? editingOp ? "Edit the activity" : "Propose a Working Group activity"
                : "Record your interest"}
          </DialogTitle>
          <DialogDescription className="dialog-description">
            {modal === "post"
              ? "Share work, ask for expertise or contribute a useful resource."
              : modal === "opportunity"
                ? "Set a clear task and requested skills. Members’ proposals are reviewed by the relevant Working Group."
                : "Describe what you can contribute. The Working Group will review your expression of interest."}
          </DialogDescription>
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              let ok = false;
              if (modal === "post")
                ok = await mutate(
                  { action: "post", body, wg: Number(postWg),mgs:postMgs,attachments:postFiles },
                  "Community update published.",
                );
              if (modal === "apply")
                ok = await mutate(
                  {
                    action: "apply",
                    opportunityId: opDetail.id,
                    message: body,
                  },
                  "Your interest has been recorded.",
                );
              if (modal === "opportunity" && editingOp)
                ok = await mutate({ action: "opportunityEdit", id: editingOp, opportunity: { ...opDraft, project: (workItems || []).some((i) => i.id === opDraft.project && i.kind === "deliverable" && i.body === "wg" + opDraft.wg) ? opDraft.project : "" } }, "Activity updated.");
              else if (modal === "opportunity")
                ok = await mutate(
                  { action: "opportunity", opportunity: { ...opDraft, project: (workItems || []).some((i) => i.id === opDraft.project && i.kind === "deliverable" && i.body === "wg" + opDraft.wg) ? opDraft.project : "" } },
                  "Activity published.",
                );
              if (ok) {
                setModal(null);
                setOpDetail(null);
                if (editingOp) { setEditingOp(null); setOpDraft(blankActivity); }
              }
            }}
            className="stack"
          >
            {modal === "opportunity" ? (
              <>
                <div className="field">
                  <label htmlFor="op-title">Activity title *</label>
                  <input
                    id="op-title"
                    required
                    maxLength={160}
                    value={opDraft.title}
                    onChange={(e) =>
                      setOpDraft({ ...opDraft, title: e.target.value })
                    }
                  />
                </div>
                <GoalPicker label="Contribution to main goals" value={opDraft.mgs} onChange={mgs=>{
                  const linked=linkedGroups(mgs);
                  setOpDraft({...opDraft,mgs,wg:linked.includes(opDraft.wg)?opDraft.wg:linked[0] || 1});
                }}/>
                <div className="field">
                  <label htmlFor="op-review-group">Reviewing Working Group</label>
                  <select id="op-review-group" required disabled={!opDraft.mgs.length || (!!editingOp && !data.admin)}
                    value={linkedGroups(opDraft.mgs).includes(opDraft.wg)?String(opDraft.wg):''}
                    onChange={e=>setOpDraft({...opDraft,wg:Number(e.target.value)})}>
                    <option value="" disabled>Select a main goal first</option>
                    {groups.filter(g=>linkedGroups(opDraft.mgs).includes(g.id)).map(g=><option key={g.id} value={g.id}>WG{g.id} · {g.short}</option>)}
                  </select>
                  <p className="micro">This group reviews the proposal. Published activities appear in every linked WG.</p>
                </div>
                {(() => {
                  const projects = (workItems || []).filter((i) => i.kind === "deliverable" && i.body === "wg" + opDraft.wg && (!opDraft.mgs.length || opDraft.mgs.includes(i.mg)));
                  return projects.length > 0 && (
                    <div className="field">
                      <label htmlFor="op-project">Part of a flagship project (optional)</label>
                      <select id="op-project" value={projects.some((p) => p.id === opDraft.project) ? opDraft.project : ""} onChange={(e) => setOpDraft({ ...opDraft, project: e.target.value })}>
                        <option value="">Not linked to a flagship project</option>
                        {projects.map((p) => <option key={p.id} value={p.id}>MG{p.mg} · {p.title}</option>)}
                      </select>
                      <p className="micro">Flagship projects are the strategic projects of the Working Group. Linking shows this activity under the project.</p>
                    </div>
                  );
                })()}
                <OptionQuestion kind="contributionTypes" label="Contribution type" value={opDraft.type} onChange={type=>setOpDraft({...opDraft,type})} categories={categories}/>
                <div className="field">
                  <label htmlFor="op-description">
                    Task & expected contribution *
                  </label>
                  <textarea
                    id="op-description"
                    required
                    maxLength={3000}
                    value={opDraft.description}
                    onChange={(e) =>
                      setOpDraft({ ...opDraft, description: e.target.value })
                    }
                  />
                </div>
                <OptionQuestion
                  kind="skills"
                  label="Requested expertise"
                  value={opDraft.skills}
                  onChange={(v) => setOpDraft({ ...opDraft, skills: v })}
                  categories={categories}
                  multiple
                />
                <div className="form-grid">
                  <div className="field">
                    <label>Regional scope</label>
                    <Pick
                      label="Activity region"
                      value={opDraft.region}
                      onChange={(v) => setOpDraft({ ...opDraft, region: v })}
                      items={opts(regions)}
                    />
                  </div>
                  <div className="field">
                    <label>Working language</label>
                    <Pick
                      label="Activity language"
                      value={opDraft.language}
                      onChange={(v) => setOpDraft({ ...opDraft, language: v })}
                      items={opts(optionsFor("languages", categories))}
                    />
                  </div>
                  <div className="field">
                    <label>Time commitment</label>
                    <Pick
                      label="Expected time commitment"
                      value={opDraft.commitment}
                      onChange={(v) =>
                        setOpDraft({ ...opDraft, commitment: v })
                      }
                      items={opts([
                        "2–4 hours / month",
                        "4–8 hours / month",
                        "8+ hours / month",
                        "Project-based",
                      ])}
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="op-deadline">Deadline (optional)</label>
                    <input
                      id="op-deadline"
                      type="date"
                      value={opDraft.deadline}
                      onChange={(e) =>
                        setOpDraft({ ...opDraft, deadline: e.target.value })
                      }
                    />
                  </div>
                </div>
                {shareBody(access, "wg" + opDraft.wg) !== null && <AttachmentPicker value={opDraft.attachments || []} onChange={(attachments) => setOpDraft((d: any) => ({ ...d, attachments }))} body={shareBody(access, "wg" + opDraft.wg) || ""} />}
              </>
            ) : (
              <>
                {modal === "post" && (<>
                  <div className="field">
                    <span>Working Group</span>
                    <Pick
                      label="Update Working Group"
                      value={postWg}
                      onChange={value=>{setPostWg(value);setPostMgs(value==="0"?[...allGoalIds]:[]);}}
                      items={[
                        { value: "0", label: "Decade-wide" },
                        ...groups.map((g) => ({
                          value: String(g.id),
                          label: "WG" + g.id + " · " + g.short,
                        })),
                      ]}
                    />
                  </div>
                  <GoalPicker label="Contribution to main goals (optional)" value={postMgs} onChange={setPostMgs}/>
                  {shareBody(access, postWg !== "0" ? "wg" + postWg : "") !== null && <AttachmentPicker value={postFiles} onChange={setPostFiles} body={shareBody(access, postWg !== "0" ? "wg" + postWg : "") || ""} />}
                </>)}
                <div className="field">
                  <label htmlFor="contribution-text">
                    {modal === "apply"
                      ? "Your proposed contribution"
                      : "Your update"}
                  </label>
                  <textarea
                    id="contribution-text"
                    required
                    maxLength={modal === "apply" ? 2000 : 3000}
                    value={body}
                    onChange={(e) => setBody(e.target.value)}
                    placeholder={
                      modal === "apply"
                        ? "What can you contribute, and what is your availability?"
                        : "Share an update with the community…"
                    }
                  />
                  <small style={{ alignSelf: "flex-end" }}>{body.length} / {modal === "apply" ? 2000 : 3000}</small>
                </div>
              </>
            )}
            <div className="row" style={{ justifyContent: "flex-end" }}>
              <button
                type="button"
                className="btn"
                onClick={() => setModal(null)}
              >
                Cancel
              </button>
              <button className="btn primary" disabled={saving} type="submit">
                {saving ? (
                  <LoaderCircle size={16} className="spinner" />
                ) : (
                  <Check size={16} />
                )}{" "}
                {modal === "post"
                  ? "Publish update"
                  : modal === "opportunity"
                    ? editingOp ? "Save the changes" : "Submit activity"
                    : "Save expression of interest"}
              </button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </PeopleContext.Provider>
  );
}
