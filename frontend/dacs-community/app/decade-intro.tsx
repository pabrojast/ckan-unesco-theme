import { useState } from "react";
import { ArrowUpRight, ChevronDown, ChevronUp, FileText } from "lucide-react";
import { asset } from "@/lib/base";

export const RESOLUTION_URL = "https://docs.un.org/en/A/RES/78/321";
export const SYNTHESIS_URL = "https://unesdoc.unesco.org/ark:/48223/pf0000397486/";
export const PUBLIC_SITE_URL = "https://www.un-cryosphere.org/en";
const KEY = "dacs-intro-collapsed";

/** A short presentation of the Decade and of the platform at the top of Home, with its two reference documents. */
export function DecadeIntro() {
  const [collapsed, setCollapsed] = useState(() => { try { return localStorage.getItem(KEY) === "1"; } catch { return false; } });
  const toggle = () => { const v = !collapsed; setCollapsed(v); try { localStorage.setItem(KEY, v ? "1" : "0"); } catch { /* storage unavailable */ } };
  if (collapsed)
    return (
      <section className="decade-intro collapsed" aria-label="About the Decade">
        <span className="eyebrow">About the Decade</span>
        <a href={SYNTHESIS_URL} target="_blank" rel="noopener noreferrer"><FileText size={14} /> Synthesis of the Decade</a>
        <a href={RESOLUTION_URL} target="_blank" rel="noopener noreferrer"><i className="un-emblem small" aria-hidden="true" /> Resolution 78/321</a>
        <button type="button" className="text-button" onClick={toggle}><ChevronDown size={14} /> Show</button>
      </section>
    );
  return (
    <section className="decade-intro" aria-labelledby="decade-intro-title">
      <div className="decade-intro-text">
        <span className="eyebrow">About the Decade</span>
        <h2 id="decade-intro-title">This is where the Decade comes together</h2>
        <p>
          On 13 August 2024, the United Nations General Assembly proclaimed 2025–2034 the <strong>Decade of Action for Cryospheric Sciences</strong>,
          a global effort to boost research and drive urgent action to protect Earth’s frozen areas. UNESCO leads its implementation through
          its Intergovernmental Hydrological Programme.
        </p>
        <p>
          <strong>DACS Community</strong> is the members’ platform of the Decade: Working Groups, committees and partners plan together here,
          share their work and follow progress towards the five Overarching Challenges and fifteen Main Goals.
        </p>
        <p className="decade-intro-motto">Science and action for a melting world</p>
        <div className="decade-intro-links">
          <a className="text-button" href={PUBLIC_SITE_URL} target="_blank" rel="noopener noreferrer">Official website of the Decade <ArrowUpRight size={14} /></a>
          <button type="button" className="text-button" onClick={toggle}><ChevronUp size={14} /> Hide this introduction</button>
        </div>
      </div>
      <div className="decade-docs" aria-label="Reference documents">
        <a className="decade-doc synthesis" href={SYNTHESIS_URL} target="_blank" rel="noopener noreferrer">
          <img src={asset("/assets/synthesis-cover.webp")} alt="Cover of the Synthesis of the Decade of Action for Cryospheric Sciences 2025–2034" loading="lazy" />
          <span className="decade-doc-text">
            <small>Reference document</small>
            <strong>Synthesis of the Decade</strong>
            <span>The vision, the five Overarching Challenges and the fifteen Main Goals.</span>
            <em>Read on UNESDOC <ArrowUpRight size={13} /></em>
          </span>
        </a>
        <a className="decade-doc resolution" href={RESOLUTION_URL} target="_blank" rel="noopener noreferrer">
          <span className="resolution-seal" aria-hidden="true"><i className="un-emblem" /><b>A/RES/78/321</b></span>
          <span className="decade-doc-text">
            <small>United Nations General Assembly</small>
            <strong>Resolution 78/321</strong>
            <span>Proclaims 2025–2034 the Decade of Action for Cryospheric Sciences.</span>
            <em>Read the resolution <ArrowUpRight size={13} /></em>
          </span>
        </a>
      </div>
    </section>
  );
}
