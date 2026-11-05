import { createContext, useContext, useState, useEffect } from "react";
import { onAuthStateChanged, signOut, User, loginUrl, registerUrl, resetUrl } from "firebase/auth";
import { auth, configured } from "@/lib/firebase";
import { applyTheme, saveTheme, storedTheme } from "@/lib/theme";
import {
  Dialog,
  DialogContent,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Users, Layers, CalendarDays, Moon, Sun } from "lucide-react";
import { photos } from "@/lib/imagery";
import { PhotoBackdrop } from "./photo";
import { asset } from "@/lib/base";
type AuthContext = {
  user: User | null;
  openSignIn: (mode?: "signin" | "register") => void;
  revision: number;
  initializing: boolean;
};
const Context = createContext<AuthContext>({
  user: null,
  openSignIn: () => {},
  revision: 0,
  initializing: true,
});
export const useMemberAuth = () => useContext(Context);
export function signOutMember() {
  if (auth) void signOut(auth);
}
export function AccountControls() {
  const { user } = useMemberAuth();
  return user ? (
    <div className="account-controls">
      <span title={user.email || ""}>Signed in as {user.email}</span>
      <button className="text-button" onClick={signOutMember}>
        Sign out
      </button>
    </div>
  ) : null;
}
/**
 * IHP-WINS edition: members sign in with their IHP-WINS account. Used on the landing page, the poll invitation
 * page and the sign-in dialog. The props of the Firebase version are kept so the callers do not change.
 */
export function AuthForm({
  mode,
  onModeChange,
}: {
  mode: string;
  onModeChange: (mode: string) => void;
  onDone?: () => void;
  registeredMessage?: string;
}) {
  const register = mode === "register";
  return (
    <>
      <Tabs className="tabs-surface wide" value={mode} onValueChange={(m) => onModeChange(m)}>
        <TabsList>
          <TabsTrigger value="signin">Sign in</TabsTrigger>
          <TabsTrigger value="register">Create account</TabsTrigger>
        </TabsList>
      </Tabs>
      <div className="auth-form">
        <p>
          {register
            ? "Create a free IHP-WINS account, then come back to this page to complete your member profile."
            : "Sign in with your IHP-WINS account. You will come back to this page."}
        </p>
        <a className="btn primary" href={register ? registerUrl() : loginUrl()}>
          {register ? "Create an IHP-WINS account" : "Sign in with IHP-WINS"}
        </a>
        {!register && (
          <a className="text-button forgot" href={resetUrl()}>
            Forgot your password?
          </a>
        )}
        <small>
          IHP-WINS is the Water Information Network System of UNESCO's Intergovernmental Hydrological Programme. The same
          account opens the community and the rest of IHP-WINS.
        </small>
      </div>
    </>
  );
}
export function ThemeSwitch() {
  const [dark, setDark] = useState(() => storedTheme() === "dark");
  return (
    <button
      type="button"
      onClick={() => {
        saveTheme(dark ? "light" : "dark");
        setDark(!dark);
      }}
    >
      {dark ? <Sun size={14} /> : <Moon size={14} />}
      {dark ? "Light mode" : "Dark mode"}
    </button>
  );
}
export function AuthGate({ children }: { children: React.ReactNode }) {
  const { user, initializing } = useMemberAuth();
  const [mode, setMode] = useState("signin");
  if (initializing)
    return (
      <main className="entry-loading" role="status">
        <img className="logo-light" src={asset("/assets/decade-logo-color.webp")} alt="" />
        <img className="logo-dark" src={asset("/assets/decade-logo-white.webp")} alt="" />
        <span className="loader-bar" />
        <span className="sr-only">Loading your account…</span>
      </main>
    );
  if (!user)
    return (
      <main className="entry-shell">
        <section className="entry-visual has-photo" aria-label="About DACS Community">
          <PhotoBackdrop photo={photos.icebergSky} eager sizes="(max-width: 860px) 100vw, 55vw" />
          <img
            className="entry-logo"
            src={asset("/assets/decade-logo-white.webp")}
            alt="Decade of Action for Cryospheric Sciences 2025–2034"
          />
          <div className="entry-copy">
            <div className="eyebrow">People. Science. Action.</div>
            <h1>The member platform of the Decade of Action for Cryospheric Sciences</h1>
            <p>
              Join the people contributing to the Decade. Sign in or create an account to access
              member profiles, Working Groups and contribution opportunities.
            </p>
            <ul className="entry-features">
              <li><Users />Member directory and expertise matching</li>
              <li><Layers />Five Working Groups, activities and contributions</li>
              <li><CalendarDays />Decade calendar, meeting polls and news</li>
            </ul>
          </div>
          <div className="entry-visual-foot">
            <img src={asset("/assets/unesco-logo-white.webp")} alt="UNESCO" />
            <span>Secretariat hosted by UNESCO–IHP</span>
          </div>
        </section>
        <section className="entry-panel">
          <div className="entry-card">
            <div>
              <div className="eyebrow">DACS Community</div>
              <h2 style={{ marginTop: 6 }}>{mode === "register" ? "Create your account" : "Sign in to your account"}</h2>
              <p className="lead">
                {mode === "register"
                  ? "Create an IHP-WINS account, then complete your member profile in five short steps."
                  : "Use your IHP-WINS account to access the community."}
              </p>
            </div>
            {configured ? (
              <AuthForm mode={mode} onModeChange={setMode} />
            ) : (
              <div className="error-banner">
                Member registration is unavailable at the moment.
              </div>
            )}
            <p className="auth-help">
              If you encounter any problem, please contact the UNESCO Secretariat by email at{" "}
              <a href="mailto:cryosphere@unesco.org">cryosphere@unesco.org</a>.
            </p>
            <div className="entry-foot">
              <span>UNESCO–IHP · 2025–2034</span>
              <ThemeSwitch />
            </div>
          </div>
        </section>
      </main>
    );
  return <>{children}</>;
}
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [revision, setRevision] = useState(0),
    [user, setUser] = useState<User | null>(null),
    [initializing, setInitializing] = useState(true),
    [open, setOpen] = useState(false),
    [mode, setMode] = useState("signin");
  useEffect(() => {
    applyTheme(storedTheme());
    if (!auth) {
      setInitializing(false);
      return;
    }
    return onAuthStateChanged(auth, (u) => {
      setUser(u);
      setInitializing(false);
    });
  }, []);
  useEffect(() => {
    const refresh = () => {
      setUser(auth?.currentUser || null);
      setRevision((v) => v + 1);
    };
    window.addEventListener("dacs-auth-refresh", refresh);
    return () => window.removeEventListener("dacs-auth-refresh", refresh);
  }, []);
  return (
    <Context.Provider
      value={{
        user,
        revision,
        initializing,
        openSignIn: (m = "signin") => {
          setMode(m);
          setOpen(true);
        },
      }}
    >
      {children}
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="detail-content auth-dialog">
          <DialogTitle>Join DACS Community</DialogTitle>
          <DialogDescription>
            Use your IHP-WINS account to create a profile and contribute to the Decade.
          </DialogDescription>
          {!configured ? (
            <p>Registration is unavailable at the moment.</p>
          ) : (
            <AuthForm mode={mode} onModeChange={setMode} onDone={() => setOpen(false)} />
          )}
        </DialogContent>
      </Dialog>
    </Context.Provider>
  );
}
