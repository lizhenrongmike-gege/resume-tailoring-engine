const fs = require("fs");
const path = require("path");
const {
  AlignmentType,
  BorderStyle,
  Document,
  LevelFormat,
  Packer,
  Paragraph,
  TabStopType,
  TextRun,
} = require("docx");

// ── SINGLE SOURCE OF TRUTH: ATS-safe formatting profile ──
// These values are tested and produce a well-filled one-page resume.
// Do NOT modify these without regenerating and verifying a PDF.
const profile = {
  page: {
    width: 12240,
    height: 15840,
    margins: { top: 720, right: 720, bottom: 720, left: 720 },
  },
  fonts: { primary: "Times New Roman" },
  sizes: {
    name: 32,
    contact: 20,
    sectionHeader: 24,
    role: 20,
    body: 20,
  },
  spacing: {
    section: { before: 70, after: 20, line: 240 },
    role: { before: 18, after: 0, line: 240 },
    bullet: { before: 0, after: 4, line: 240 },
    body: { before: 0, after: 4, line: 240 },
  },
  bullets: { indentLeft: 360, indentHanging: 180 },
  rightTab: 11040,
  divider: { borderStyle: "single", borderSize: 4, borderColor: "000000" },
};

const FONT = profile.fonts.primary;

// ── HELPER FUNCTIONS ──

function bodyRun(text, extra = {}) {
  return new TextRun({ text, font: FONT, size: profile.sizes.body, ...extra });
}

function centeredParagraph(text, size, bold = false) {
  return new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: profile.spacing.body,
    children: [new TextRun({ text, font: FONT, size, bold })],
  });
}

function sectionHeader(text) {
  return new Paragraph({
    spacing: profile.spacing.section,
    border: {
      bottom: {
        style: BorderStyle[profile.divider.borderStyle.toUpperCase()],
        size: profile.divider.borderSize,
        color: profile.divider.borderColor,
        space: 1,
      },
    },
    children: [
      new TextRun({
        text: text.toUpperCase(),
        font: FONT,
        size: profile.sizes.sectionHeader,
        bold: true,
      }),
    ],
  });
}

function bodyParagraph(text) {
  return new Paragraph({
    spacing: profile.spacing.body,
    children: [bodyRun(text)],
  });
}

function roleHeader(title, company, location, dates) {
  return [
    new Paragraph({
      spacing: profile.spacing.role,
      tabStops: [{ type: TabStopType.RIGHT, position: profile.rightTab }],
      children: [
        new TextRun({ text: company, font: FONT, size: profile.sizes.role, bold: true }),
        new TextRun({ text: "\t", font: FONT, size: profile.sizes.role }),
        new TextRun({ text: location, font: FONT, size: profile.sizes.role }),
      ],
    }),
    new Paragraph({
      spacing: { before: 0, after: 0, line: profile.spacing.role.line },
      tabStops: [{ type: TabStopType.RIGHT, position: profile.rightTab }],
      children: [
        new TextRun({ text: title, font: FONT, size: profile.sizes.role, italics: true }),
        new TextRun({ text: "\t", font: FONT, size: profile.sizes.role }),
        new TextRun({ text: dates, font: FONT, size: profile.sizes.role, italics: true }),
      ],
    }),
  ];
}

function projectHeader(name, dates) {
  return new Paragraph({
    spacing: profile.spacing.role,
    tabStops: [{ type: TabStopType.RIGHT, position: profile.rightTab }],
    children: [
      new TextRun({ text: name, font: FONT, size: profile.sizes.role, bold: true }),
      new TextRun({ text: "\t", font: FONT, size: profile.sizes.role }),
      new TextRun({ text: dates, font: FONT, size: profile.sizes.role, italics: true }),
    ],
  });
}

function bulletParagraph(text) {
  return new Paragraph({
    numbering: { reference: "bullets", level: 0 },
    spacing: profile.spacing.bullet,
    children: [bodyRun(text)],
  });
}

// ── DOCUMENT BUILDER ──

/**
 * Build a .docx resume from a content object.
 *
 * @param {Object} content - Resume content
 * @param {string} content.name
 * @param {string} content.contact
 * @param {string} content.summary
 * @param {string} content.skills
 * @param {Array}  content.workExperience - [{company, location, title, dates, bullets: [string]}]
 * @param {Array}  [content.selectedProjects] - [{name, dates, bullets: [string]}]
 * @param {Object} content.education - {school, location, degree, date, details}
 * @param {string} [outputPath] - If provided, writes the .docx to this path
 * @returns {Promise<Buffer>} The .docx file buffer
 */
async function buildDocument(content, outputPath) {
  const children = [
    new Paragraph({
      spacing: profile.spacing.body,
      children: [new TextRun({ text: content.name, font: FONT, size: profile.sizes.name, bold: true })],
    }),
    ...(Array.isArray(content.contact) ? content.contact : [content.contact]).map(
      (line) =>
        new Paragraph({
          spacing: { before: 0, after: 0, line: profile.spacing.body.line },
          children: [new TextRun({ text: line, font: FONT, size: profile.sizes.contact })],
        }),
    ),
    sectionHeader("Professional Summary"),
    bodyParagraph(content.summary),
    sectionHeader("Skills"),
    bodyParagraph(content.skills),
    sectionHeader("Work Experience"),
  ];

  for (const role of content.workExperience) {
    children.push(...roleHeader(role.title, role.company, role.location, role.dates));
    for (const item of role.bullets) {
      children.push(bulletParagraph(item));
    }
  }

  if (content.selectedProjects && content.selectedProjects.length > 0) {
    children.push(sectionHeader("Selected Projects"));
    for (const project of content.selectedProjects) {
      children.push(projectHeader(project.name, project.dates));
      for (const item of project.bullets) {
        children.push(bulletParagraph(item));
      }
    }
  }

  children.push(sectionHeader("Education"));
  children.push(
    new Paragraph({
      spacing: profile.spacing.role,
      tabStops: [{ type: TabStopType.RIGHT, position: profile.rightTab }],
      children: [
        new TextRun({
          text: content.education.school,
          font: FONT,
          size: profile.sizes.role,
          bold: true,
        }),
        new TextRun({ text: "\t", font: FONT, size: profile.sizes.role }),
        new TextRun({ text: content.education.location, font: FONT, size: profile.sizes.role }),
      ],
    }),
  );
  children.push(
    new Paragraph({
      spacing: { before: 0, after: 0, line: profile.spacing.role.line },
      tabStops: [{ type: TabStopType.RIGHT, position: profile.rightTab }],
      children: [
        new TextRun({
          text: content.education.degree,
          font: FONT,
          size: profile.sizes.role,
          italics: true,
        }),
        new TextRun({ text: "\t", font: FONT, size: profile.sizes.role }),
        new TextRun({
          text: content.education.date,
          font: FONT,
          size: profile.sizes.role,
          italics: true,
        }),
      ],
    }),
  );
  children.push(bodyParagraph(content.education.details));

  const doc = new Document({
    numbering: {
      config: [
        {
          reference: "bullets",
          levels: [
            {
              level: 0,
              format: LevelFormat.BULLET,
              text: "\u2022",
              alignment: AlignmentType.LEFT,
              style: {
                paragraph: {
                  indent: {
                    left: profile.bullets.indentLeft,
                    hanging: profile.bullets.indentHanging,
                  },
                },
              },
            },
          ],
        },
      ],
    },
    sections: [
      {
        properties: {
          page: {
            size: { width: profile.page.width, height: profile.page.height },
            margin: profile.page.margins,
          },
        },
        children,
      },
    ],
  });

  const buffer = await Packer.toBuffer(doc);

  if (outputPath) {
    const dir = path.dirname(outputPath);
    fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(outputPath, buffer);
    console.log(`Wrote ${outputPath}`);
  }

  return buffer;
}

// ── PAGE FILL ESTIMATOR ──

/**
 * Estimate page fill from a content object BEFORE generating the .docx.
 * Predicts vertical space usage and content line count so the agent can
 * adjust content without the expensive generate → convert → check cycle.
 *
 * @param {Object} content - Same content object passed to buildDocument
 * @returns {Object} Estimation results:
 *   - estimatedLines: predicted non-empty content lines
 *   - estimatedHeightDXA: total vertical space consumed
 *   - availableHeightDXA: usable page height (page minus margins)
 *   - fillPercent: height as % of available (100 = exactly full)
 *   - totalBullets: count of all bullet strings
 *   - totalBulletChars: sum of all bullet character lengths
 *   - verdict: "OVER" | "OK" | "UNDER"
 */
function estimatePageFill(content) {
  // Characters per line at 10pt Times New Roman on US Letter with 0.5" margins
  const BODY_CPL = 95;       // body text: 7.5" content width
  const BULLET_CPL = 90;     // bullets: indented, ~7.25" content width
  const LINE_H = 220;        // single line height in DXA (slightly tighter)
  const AVAILABLE_H =
    profile.page.height - profile.page.margins.top - profile.page.margins.bottom;

  let heightDXA = 0;
  let contentLines = 0;
  let totalBullets = 0;
  let totalBulletChars = 0;

  // Helper: add a paragraph's vertical cost
  function addParagraph(spacing, textLines) {
    heightDXA += spacing.before + textLines * LINE_H + spacing.after;
    contentLines += textLines;
  }

  function textLines(text, cpl) {
    return Math.ceil((text || "").length / cpl) || 1;
  }

  // Name + Contact
  addParagraph(profile.spacing.body, 1);
  const contactLines = Array.isArray(content.contact) ? content.contact.length : 1;
  for (let i = 0; i < contactLines; i++) {
    addParagraph({ before: 0, after: 0, line: profile.spacing.body.line }, 1);
  }

  // Professional Summary
  addParagraph(profile.spacing.section, 1); // header
  addParagraph(profile.spacing.body, textLines(content.summary, BODY_CPL));

  // Skills
  addParagraph(profile.spacing.section, 1);
  addParagraph(profile.spacing.body, textLines(content.skills, BODY_CPL));

  // Work Experience
  addParagraph(profile.spacing.section, 1); // header
  for (const role of content.workExperience || []) {
    // Role header: company/location line + title/dates line
    addParagraph(profile.spacing.role, 1);
    heightDXA += LINE_H; // title/dates line (no extra spacing)
    contentLines += 1;
    for (const bullet of role.bullets || []) {
      addParagraph(profile.spacing.bullet, textLines(bullet, BULLET_CPL));
      totalBullets++;
      totalBulletChars += bullet.length;
    }
  }

  // Selected Projects
  if (content.selectedProjects && content.selectedProjects.length > 0) {
    addParagraph(profile.spacing.section, 1);
    for (const project of content.selectedProjects) {
      addParagraph(profile.spacing.role, 1); // project header
      for (const bullet of project.bullets || []) {
        addParagraph(profile.spacing.bullet, textLines(bullet, BULLET_CPL));
        totalBullets++;
        totalBulletChars += bullet.length;
      }
    }
  }

  // Education
  addParagraph(profile.spacing.section, 1); // header
  addParagraph(profile.spacing.role, 1);    // school/location
  heightDXA += LINE_H;                      // degree/date (no extra spacing)
  contentLines += 1;
  addParagraph(
    profile.spacing.body,
    textLines(content.education?.details, BODY_CPL),
  );

  // Verdict — estimate has ~3-5% margin of error vs actual rendering
  const fillPct = Math.round((heightDXA / AVAILABLE_H) * 100);
  let verdict;
  if (fillPct > 100) {
    verdict = "OVER";
  } else if (fillPct < 80) {
    verdict = "UNDER";
  } else {
    verdict = "OK";
  }

  return {
    estimatedLines: contentLines,
    estimatedHeightDXA: heightDXA,
    availableHeightDXA: AVAILABLE_H,
    fillPercent: fillPct,
    totalBullets,
    totalBulletChars,
    verdict,
  };
}

module.exports = { profile, buildDocument, estimatePageFill };
