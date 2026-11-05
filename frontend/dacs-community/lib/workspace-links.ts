// SharePoint working-document folders of the Decade (DACS SharePoint site, Shared Documents).
// Shown to protected leadership and Core Group roles of any body. Folder permissions are managed in SharePoint.
const base = "https://unesco.sharepoint.com/:f:/r/sites/DecadeofActionforCryosphericSciences2025-2034/Shared%20Documents/";
export type DocumentFolder = { id: string; folder: string; href: string };
export const documentFolders: DocumentFolder[] = [
  { id: "general", folder: "General information from UNESCO IHP Secretariat", href: base + "0%20-General%20information%20from%20UNESCO%20IHP%20Secretariat?d=wd03d1d17435440bcb6bac14f6f3faf06&csf=1&web=1&e=zBaNVI" },
  { id: "wg1", folder: "WG1 - Global Cryosphere Monitoring", href: base + "WG1%20-%20Global%20Cryosphere%20Monitoring?d=w75fb4554f4634669b8f54af83896827b&csf=1&web=1&e=x6p9jE" },
  { id: "wg2", folder: "WG2 - Actionable Cryosphere Projection", href: base + "WG2%20-%20Actionable%20Cryosphere%20Projection?d=w3706133eb41e4373afe41a7a56e27f55&csf=1&web=1&e=aotbLN" },
  { id: "wg3", folder: "WG3 - Cryospheric Risk Management Solutions", href: base + "WG3%20-%20Cryospheric%20Risk%20Management%20Solutions?d=wa4a84fa3f56747c89d413437dc3e6bd2&csf=1&web=1&e=GMpgKr" },
  { id: "wg4", folder: "WG4 - Adaptation to Cryosphere Loss", href: base + "WG4%20-%20Adaptation%20to%20Cryosphere%20Loss?d=w77694fa883c04f79a3f0e6b9bb1f37a9&csf=1&web=1&e=C6zIUJ" },
  { id: "wg5", folder: "WG5 - Amplify the Impact of Cryospheric Science", href: base + "WG5%20-%20Amplify%20the%20Impact%20of%20Cryospheric%20Science?d=we95cd5cc1a784bccafecce2c7927c139&csf=1&web=1&e=3GmGZi" },
  { id: "smc", folder: "SMC - Strategic Management Committee", href: base + "SMC%20-%20Strategic%20Management%20Committee?d=wbd0ceb74d149434db557229e97eab955&csf=1&web=1&e=r9jXxc" },
  { id: "esc", folder: "ESC - Executive Steering Committee", href: base + "ESC%20-%20Executive%20Steering%20Committee?d=w58df3aec76d84be18c345b6572e6dca9&csf=1&web=1&e=76p0gT" },
  { id: "cfd", folder: "CFD - Cryosphere Finance Dialogue", href: base + "CFD%20-%20Cryosphere%20Finance%20Dialogue?d=w91cc2e906ed846eeb51e4fb52768b11d&csf=1&web=1&e=yfv6Nc" },
  { id: "alliance", folder: "Alliance for the Cryosphere", href: base + "Alliance%20for%20the%20Cryosphere?d=w79e120aa82f947a5aa74e43dd0a9623e&csf=1&web=1&e=o2rJ1Q" },
];
export const documentFolder = (id: string) => documentFolders.find((f) => f.id === id);
