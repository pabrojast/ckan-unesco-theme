import { ArrowUpRight, Download, FileArchive, Presentation } from "lucide-react";
import { logoApplicationUrl } from "./resources";
import { asset, BASE } from "@/lib/base";

const template = { href: asset("assets/templates/DACS_slide_template.pptx"), file: "DACS_slide_template.pptx", slides: 22, size: "7 MB" };
const slide = (n: number) => `${BASE}assets/templates/previews/slide-${String(n).padStart(2, "0")}.webp`;
const logos = [
  { id: "en", language: "English", native: "English", dir: "ltr" },
  { id: "fr", language: "French", native: "Français", dir: "ltr" },
  { id: "es", language: "Spanish", native: "Español", dir: "ltr" },
  { id: "ar", language: "Arabic", native: "العربية", dir: "rtl" },
  { id: "zh", language: "Chinese", native: "中文", dir: "ltr" },
  { id: "ru", language: "Russian", native: "Русский", dir: "ltr" },
];

/** Templates: the Decade presentation template and the logo of the Decade in the six official UN languages. */
export function Templates() {
  return (
    <section className="templates">
      <article className="glass template-hero">
        <a className="template-cover" href={template.href} download={template.file} aria-label="Download the presentation template">
          <img src={slide(1)} alt="Title slide of the Decade presentation template" />
        </a>
        <div className="template-copy">
          <span className="eyebrow"><Presentation size={14} /> Presentation template</span>
          <h2>Decade of Action for Cryospheric Sciences slide template</h2>
          <p>Title, section, content, figures and closing slides in the visual identity of the Decade, with the logos of the Decade and UNESCO already in place.</p>
          <div className="template-meta"><span>PowerPoint (.pptx)</span><span>{template.slides} slides</span><span>{template.size}</span></div>
          <a className="btn primary" href={template.href} download={template.file}><Download size={16} /> Download the template</a>
        </div>
      </article>

      <div className="subsection-title templates-logos-head">
        <span>Logo of the Decade in the six official languages</span>
        <a className="btn small" href={asset("/assets/logos/decade-logos-six-languages.zip")} download><FileArchive size={14} /> Download all (ZIP)</a>
      </div>
      <p className="micro templates-hint">White versions with a transparent background, for dark or photographic backgrounds. PNG, 3754 × 964 pixels.</p>
      <div className="logo-grid">
        {logos.map((l) => (
          <article className="logo-card" key={l.id}>
            <div className="logo-stage"><img src={`${BASE}assets/logos/decade-logo-${l.id}-white-preview.webp`} alt={`Logo of the Decade in ${l.language}`} loading="lazy" /></div>
            <div className="logo-foot">
              <span><strong>{l.language}</strong>{l.native !== l.language && <small dir={l.dir} lang={l.id}>{l.native}</small>}</span>
              <a className="btn small" href={`${BASE}assets/logos/decade-logo-${l.id}-white.png`} download={`decade-logo-${l.id}-white.png`}><Download size={14} /> PNG</a>
            </div>
          </article>
        ))}
      </div>
      <p className="notice templates-rule">
        <span>To place the logo of the Decade on an activity, publication or event of your own, apply first for authorisation.</span>
        <a className="text-button" href={logoApplicationUrl} target="_blank" rel="noopener noreferrer">Apply to carry the logo <ArrowUpRight size={13} /></a>
      </p>

    </section>
  );
}
