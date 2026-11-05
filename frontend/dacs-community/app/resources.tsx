import { Globe, FolderOpen, MessageSquare, BadgeCheck, ArrowUpRight, FilePenLine } from "lucide-react";
import { photos } from "@/lib/imagery";
import { documentFolders } from "@/lib/workspace-links";
import { PhotoCredit } from "./photo";
export const publicWebsite = "https://www.un-cryosphere.org/en";
export const shareContentUrl = "https://www.un-cryosphere.org/en/get-involved/share";
export const logoApplicationUrl = "https://www.un-cryosphere.org/en/get-involved/submit-activity";
const links = [
  { title: "SharePoint", text: "Documents and group work", href: "https://unesco.sharepoint.com/sites/DecadeofActionforCryosphericSciences2025-2034", Icon: FolderOpen },
  { title: "Microsoft Teams", text: "Meetings and conversations", href: "https://teams.microsoft.com/l/team/19%3Ax4MX0CKUzMLyRJPaJvmv167OIRPfM5Mvfbc2nOFohiY1%40thread.tacv2/conversations?groupId=0ee25b6e-b45c-403e-8dac-05afbe631455&tenantId=1d4fae52-39b3-4bfa-b0b3-022956b11194", Icon: MessageSquare },
];
export function OfficialWebsite() {
  const photo = photos.icebergsAerial;
  return <div className="stack">
    <div className="feature-wrap">
      <a href={publicWebsite} className="glass resource-card feature" target="_blank" rel="noopener noreferrer">
        <img className="photo-backdrop" src={photo.src} srcSet={`${photo.small} 800w, ${photo.src} 1600w`} sizes="(max-width: 800px) 100vw, 1200px" alt="" decoding="async" style={{ objectPosition: photo.position }} />
        <Globe size={25}/><div><h2>United Nations Cryosphere Decade</h2><p>News, events and public resources · un-cryosphere.org</p></div><ArrowUpRight size={20}/>
      </a>
      <PhotoCredit photo={photo} />
    </div>
    <PublicResources />
  </div>;
}
export function PublicResources() {
  return <section className="workspace-links" aria-label="Public Decade resources">
    <div className="section-title" style={{ marginBottom: 0 }}><h2>Contribute to the official website</h2></div>
    <div className="resource-grid public-resource-grid">
      <a href={shareContentUrl} className="resource-card" target="_blank" rel="noopener noreferrer"><FilePenLine size={24}/><div><h3>Publish your content on the official website of the Decade</h3><p>Submit news, events and projects</p></div><ArrowUpRight size={18}/></a>
      <a href={logoApplicationUrl} className="resource-card" target="_blank" rel="noopener noreferrer"><BadgeCheck size={24}/><div><h3>Apply to carry the logo of the Decade</h3><p>Submit an activity for logo authorisation</p></div><ArrowUpRight size={18}/></a>
    </div>
    <p className="micro">The forms open on the official website in a new tab.</p>
  </section>;
}
export function CoreWorkspace() {
  return <div className="stack">
    <section className="glass library-intro" aria-label="About the SharePoint library">
      <span className="library-icon" aria-hidden="true"><FolderOpen size={26}/></span>
      <div>
        <h2>All working documents are stored on SharePoint</h2>
        <p>The leadership and Core Group members of the Decade bodies have access to the Decade SharePoint site, where they collaborate on these documents.</p>
        <p className="library-help">If you cannot access the platform, please contact the UNESCO Secretariat at <a href="mailto:cryosphere@unesco.org">cryosphere@unesco.org</a>.</p>
      </div>
    </section>
    <section className="workspace-links" aria-label="SharePoint and Microsoft Teams">
      <div className="resource-grid">{links.map(({title,text,href,Icon}) =>
        <a key={title} href={href} className="resource-card" target="_blank" rel="noopener noreferrer">
          <Icon size={22}/><div><h3>{title}</h3><p>{text}</p></div><ArrowUpRight size={16}/>
        </a>
      )}</div>
          </section>
    <section className="workspace-links" aria-labelledby="document-folders-title">
      <div className="section-title" style={{ marginBottom: 0 }}><h2 id="document-folders-title">Folders of the Decade bodies</h2></div>
      <div className="resource-grid folder-grid">{documentFolders.map((f) =>
        <a key={f.id} href={f.href} className="resource-card folder-card" target="_blank" rel="noopener noreferrer">
          <FolderOpen size={20}/><div><h3>{f.folder}</h3><p>Shared documents folder</p></div><ArrowUpRight size={16}/>
        </a>
      )}</div>
    </section>
  </div>;
}
