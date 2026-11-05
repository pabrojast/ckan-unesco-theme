import test from 'node:test';
import assert from 'node:assert/strict';
import {documentFolders,documentFolder} from '../lib/workspace-links.ts';
// Exact links supplied by the UNESCO Secretariat, 11 October 2026.
const expected={
 general:'https://unesco.sharepoint.com/:f:/r/sites/DecadeofActionforCryosphericSciences2025-2034/Shared%20Documents/0%20-General%20information%20from%20UNESCO%20IHP%20Secretariat?d=wd03d1d17435440bcb6bac14f6f3faf06&csf=1&web=1&e=zBaNVI',
 wg1:'https://unesco.sharepoint.com/:f:/r/sites/DecadeofActionforCryosphericSciences2025-2034/Shared%20Documents/WG1%20-%20Global%20Cryosphere%20Monitoring?d=w75fb4554f4634669b8f54af83896827b&csf=1&web=1&e=x6p9jE',
 wg2:'https://unesco.sharepoint.com/:f:/r/sites/DecadeofActionforCryosphericSciences2025-2034/Shared%20Documents/WG2%20-%20Actionable%20Cryosphere%20Projection?d=w3706133eb41e4373afe41a7a56e27f55&csf=1&web=1&e=aotbLN',
 wg3:'https://unesco.sharepoint.com/:f:/r/sites/DecadeofActionforCryosphericSciences2025-2034/Shared%20Documents/WG3%20-%20Cryospheric%20Risk%20Management%20Solutions?d=wa4a84fa3f56747c89d413437dc3e6bd2&csf=1&web=1&e=GMpgKr',
 wg4:'https://unesco.sharepoint.com/:f:/r/sites/DecadeofActionforCryosphericSciences2025-2034/Shared%20Documents/WG4%20-%20Adaptation%20to%20Cryosphere%20Loss?d=w77694fa883c04f79a3f0e6b9bb1f37a9&csf=1&web=1&e=C6zIUJ',
 wg5:'https://unesco.sharepoint.com/:f:/r/sites/DecadeofActionforCryosphericSciences2025-2034/Shared%20Documents/WG5%20-%20Amplify%20the%20Impact%20of%20Cryospheric%20Science?d=we95cd5cc1a784bccafecce2c7927c139&csf=1&web=1&e=3GmGZi',
 smc:'https://unesco.sharepoint.com/:f:/r/sites/DecadeofActionforCryosphericSciences2025-2034/Shared%20Documents/SMC%20-%20Strategic%20Management%20Committee?d=wbd0ceb74d149434db557229e97eab955&csf=1&web=1&e=r9jXxc',
 esc:'https://unesco.sharepoint.com/:f:/r/sites/DecadeofActionforCryosphericSciences2025-2034/Shared%20Documents/ESC%20-%20Executive%20Steering%20Committee?d=w58df3aec76d84be18c345b6572e6dca9&csf=1&web=1&e=76p0gT',
 cfd:'https://unesco.sharepoint.com/:f:/r/sites/DecadeofActionforCryosphericSciences2025-2034/Shared%20Documents/CFD%20-%20Cryosphere%20Finance%20Dialogue?d=w91cc2e906ed846eeb51e4fb52768b11d&csf=1&web=1&e=yfv6Nc',
 alliance:'https://unesco.sharepoint.com/:f:/r/sites/DecadeofActionforCryosphericSciences2025-2034/Shared%20Documents/Alliance%20for%20the%20Cryosphere?d=w79e120aa82f947a5aa74e43dd0a9623e&csf=1&web=1&e=o2rJ1Q',
};
test('every SharePoint folder link matches the supplied address exactly',()=>{assert.equal(documentFolders.length,Object.keys(expected).length);for(const [id,href] of Object.entries(expected))assert.equal(documentFolder(id)?.href,href,id);assert.equal(documentFolder('iac'),undefined);});
