"""Hardcoded test content for all asset templates."""

from app.assets.models import (
    BrandingConfig,
    CaseStudyPageInput,
    DemoRequestPageInput,
    DocumentAdInput,
    FormField,
    LeadMagnetPageInput,
    LeadMagnetPDFInput,
    MetricCallout,
    PDFSection,
    Section,
    Slide,
    SocialProofConfig,
    TrackingConfig,
    WebinarPageInput,
)

NEXUS_BRANDING = BrandingConfig(
    logo_url=None,
    primary_color="#00e87b",
    secondary_color="#09090b",
    font_family="Inter, sans-serif",
    company_name="Nexus Security",
)

TRACKING = TrackingConfig()

# ---------------------------------------------------------------------------
# LP-1: Lead Magnet Download Page
# ---------------------------------------------------------------------------
LEAD_MAGNET_PAGE = LeadMagnetPageInput(
    headline="The Complete CMMC Compliance Checklist for Federal Contractors",
    subhead="67% of contractors fail their first CMMC assessment. Don't be one of them.",
    value_props=[
        "Step-by-step checklist covering all 14 CMMC Level 2 domains",
        "Real-world remediation priorities ranked by audit failure frequency",
        "Pre-built evidence collection templates for your assessment",
        "Timeline planner to get assessment-ready in 90 days",
    ],
    form_fields=[
        FormField(name="first_name", label="First Name"),
        FormField(name="last_name", label="Last Name"),
        FormField(name="email", label="Work Email", type="email"),
        FormField(name="company", label="Company"),
    ],
    cta_text="Download the Checklist",
    branding=NEXUS_BRANDING,
    tracking=TRACKING,
    social_proof=SocialProofConfig(
        type="stats",
        stats=[
            MetricCallout(value="200+", label="Federal Contractors"),
            MetricCallout(value="98%", label="Pass Rate"),
            MetricCallout(value="45 days", label="Avg. Time to Ready"),
        ],
    ),
)

# ---------------------------------------------------------------------------
# LP-2: Case Study Page
# ---------------------------------------------------------------------------
CASE_STUDY_PAGE = CaseStudyPageInput(
    customer_name="Acme Corp",
    headline="How Acme Corp Reduced Breach Risk by 73% with Nexus Security",
    sections=[
        Section(
            heading="The Situation",
            body="Acme Corp, a mid-market federal contractor with 850 employees, was preparing for their first CMMC Level 2 assessment. With contracts worth $47M at stake, passing wasn't optional — it was existential.",
        ),
        Section(
            heading="The Challenge",
            body="An internal gap assessment revealed critical shortfalls across access control, incident response, and configuration management. Their existing security tools were siloed, manually managed, and produced no auditable evidence trail.",
            bullets=[
                "No centralized identity management across 12 disparate systems",
                "Incident response playbooks existed on paper but had never been tested",
                "Configuration baselines were undocumented for 340+ endpoints",
                "Evidence collection for auditors would have taken an estimated 6 months manually",
            ],
        ),
        Section(
            heading="The Solution",
            body="Acme deployed Nexus Security's unified compliance platform across their entire infrastructure in a phased 14-day rollout. The platform automated evidence collection, continuously monitored compliance posture, and provided a real-time dashboard mapping controls to CMMC requirements.",
            callout="\"We went from dreading the assessment to actually looking forward to showing auditors our dashboard.\" — CISO, Acme Corp",
        ),
        Section(
            heading="The Results",
            body="Within 90 days of deployment, Acme Corp passed their CMMC Level 2 assessment on the first attempt — joining the 33% of contractors who don't need a second try.",
            bullets=[
                "73% reduction in identified security gaps within 60 days",
                "$2.1M saved vs. projected cost of manual compliance effort",
                "14-day full deployment across all 850 endpoints",
                "99.9% platform uptime during the assessment period",
            ],
        ),
    ],
    metrics=[
        MetricCallout(value="73%", label="Risk Reduction"),
        MetricCallout(value="$2.1M", label="Cost Savings"),
        MetricCallout(value="14 days", label="Deployment Time"),
        MetricCallout(value="99.9%", label="Platform Uptime"),
    ],
    quote_text="Nexus Security didn't just help us pass our assessment — they fundamentally changed how we think about security. We went from checkbox compliance to genuine security posture improvement.",
    quote_author="Sarah Chen",
    quote_title="CISO, Acme Corp",
    cta_text="Get Similar Results",
    form_fields=[
        FormField(name="first_name", label="First Name"),
        FormField(name="last_name", label="Last Name"),
        FormField(name="email", label="Work Email", type="email"),
        FormField(name="company", label="Company"),
    ],
    branding=NEXUS_BRANDING,
    tracking=TRACKING,
)

# ---------------------------------------------------------------------------
# LP-3: Webinar Registration Page
# ---------------------------------------------------------------------------
WEBINAR_PAGE = WebinarPageInput(
    event_name="CMMC 2.0: What Changed and What You Need to Do Now",
    event_date="April 15, 2026 at 1:00 PM ET",
    headline="CMMC 2.0 Is Here — Are You Ready for the New Requirements?",
    speakers=[
        {
            "name": "Dr. James Morrison",
            "title": "VP of Compliance",
            "company": "Nexus Security",
        },
        {
            "name": "Col. (Ret.) Patricia Wells",
            "title": "Former CMMC-AB Board Member",
            "company": "Wells Advisory Group",
        },
        {
            "name": "Michael Torres",
            "title": "CISO",
            "company": "DefenseTech Inc.",
        },
    ],
    agenda=[
        "Key changes between CMMC 1.0 and 2.0 — what contractors must know",
        "Timeline breakdown: when each level takes effect and what triggers assessment",
        "Live walkthrough: mapping your existing controls to the new framework",
        "Panel Q&A: real questions from federal contractors answered by experts",
    ],
    form_fields=[
        FormField(name="first_name", label="First Name"),
        FormField(name="last_name", label="Last Name"),
        FormField(name="email", label="Work Email", type="email"),
        FormField(name="company", label="Company"),
        FormField(name="job_title", label="Job Title"),
    ],
    cta_text="Register Now",
    branding=NEXUS_BRANDING,
    tracking=TRACKING,
)

# ---------------------------------------------------------------------------
# LP-4: Demo Request Page
# ---------------------------------------------------------------------------
DEMO_REQUEST_PAGE = DemoRequestPageInput(
    headline="Stop Guessing About Your Compliance Posture",
    subhead="See how Nexus Security gives federal contractors real-time visibility into CMMC readiness — with automated evidence collection and continuous monitoring.",
    benefits=[
        Section(
            heading="Automated Evidence Collection",
            body="Eliminate manual screenshot gathering and spreadsheet tracking. Nexus continuously collects and organizes audit evidence mapped to every CMMC control.",
            bullets=[
                "Auto-maps to all 110 CMMC Level 2 practices",
                "Generates auditor-ready evidence packages on demand",
                "Reduces evidence collection time by 85%",
            ],
        ),
        Section(
            heading="Real-Time Compliance Dashboard",
            body="Know your exact compliance posture at any moment. Our live dashboard shows gap status, remediation progress, and assessment readiness scores across every domain.",
            bullets=[
                "Domain-by-domain readiness scoring",
                "Automated alerts when controls drift out of compliance",
                "Executive-ready reports in one click",
            ],
        ),
        Section(
            heading="14-Day Deployment, Zero Disruption",
            body="Get fully operational in two weeks without disrupting your team's workflow. Our deployment playbook has been refined across 200+ contractor environments.",
            bullets=[
                "Agentless deployment for most data sources",
                "Pre-built integrations with Azure AD, AWS, CrowdStrike, and 40+ tools",
                "Dedicated onboarding engineer for your first 30 days",
            ],
        ),
    ],
    trust_signals=SocialProofConfig(
        type="stats",
        stats=[
            MetricCallout(value="200+", label="Contractors Protected"),
            MetricCallout(value="98%", label="First-Attempt Pass Rate"),
            MetricCallout(value="4.9/5", label="Customer Satisfaction"),
        ],
    ),
    form_fields=[
        FormField(name="first_name", label="First Name"),
        FormField(name="last_name", label="Last Name"),
        FormField(name="email", label="Work Email", type="email"),
        FormField(name="company", label="Company"),
        FormField(name="phone", label="Phone", type="tel", required=False),
    ],
    cta_text="Request Your Demo",
    branding=NEXUS_BRANDING,
    tracking=TRACKING,
)

# ---------------------------------------------------------------------------
# PDF-1: Lead Magnet PDF
# ---------------------------------------------------------------------------
LEAD_MAGNET_PDF = LeadMagnetPDFInput(
    title="CMMC Compliance Checklist for Federal Contractors",
    subtitle="A practical guide to achieving CMMC Level 2 certification",
    sections=[
        PDFSection(
            heading="Access Control (AC)",
            body="Access control is the foundation of CMMC compliance. These requirements ensure that only authorized users can access Controlled Unclassified Information (CUI) and that access is limited to what each user needs to perform their job function.",
            bullets=[
                "Implement role-based access control (RBAC) across all systems handling CUI",
                "Enforce multi-factor authentication for all remote access and privileged accounts",
                "Document and review access permissions quarterly, revoking access within 24 hours of role change",
                "Implement session lock after 15 minutes of inactivity on all workstations",
                "Control and monitor all remote access sessions with full audit logging",
                "Restrict wireless access to CUI systems using 802.1X authentication",
                "Encrypt all remote access sessions end-to-end",
            ],
            callout_box="Critical Requirement: AC.L2-3.1.1 — Limit system access to authorized users. This is the #1 most-cited finding in failed CMMC assessments.",
        ),
        PDFSection(
            heading="Awareness and Training (AT)",
            body="Security awareness training ensures that all personnel understand their responsibilities for protecting CUI. Training must be role-specific and documented with completion records maintained for audit purposes.",
            bullets=[
                "Conduct initial security awareness training within 30 days of onboarding",
                "Deliver role-specific training for IT administrators and security personnel",
                "Execute quarterly phishing simulation campaigns with documented results",
                "Maintain training completion records for all personnel with CUI access",
                "Update training content within 30 days of any significant threat landscape change",
            ],
            callout_box="Best Practice: Track training completion rates by department. Auditors want to see 100% completion — even one gap can trigger a finding.",
        ),
        PDFSection(
            heading="Audit and Accountability (AU)",
            body="Audit logging creates the evidence trail that proves your controls are working. Without comprehensive logging, you cannot demonstrate compliance even if your controls are technically in place.",
            bullets=[
                "Enable audit logging on all systems that process, store, or transmit CUI",
                "Include timestamp, user identity, event type, and outcome in all audit records",
                "Protect audit logs from unauthorized access, modification, and deletion",
                "Retain audit logs for a minimum of 12 months, with 90 days immediately accessible",
                "Configure automated alerts for audit log failures or storage capacity warnings",
                "Review audit logs weekly for anomalous activity patterns",
            ],
            callout_box="Automation Tip: SIEM integration is not required by CMMC, but automated log aggregation and alerting dramatically reduces the manual review burden.",
        ),
        PDFSection(
            heading="Configuration Management (CM)",
            body="Configuration management ensures that your IT systems are set up securely and stay that way. Baseline configurations prevent drift, while change management ensures modifications are tracked and authorized.",
            bullets=[
                "Establish and document baseline configurations for all system types (servers, workstations, network devices)",
                "Implement automated configuration monitoring to detect drift from baselines",
                "Maintain a complete and current inventory of all IT assets with CUI access",
                "Require documented change requests with security impact analysis for all configuration changes",
                "Restrict software installation to IT-approved applications only",
                "Disable all unnecessary services, ports, and protocols on every system",
                "Apply security configuration benchmarks (CIS or DISA STIGs) to all systems",
            ],
            callout_box="Common Pitfall: Shadow IT. Unapproved SaaS tools and personal devices accessing CUI are the most common CM finding. Conduct quarterly SaaS audits.",
        ),
        PDFSection(
            heading="Identification and Authentication (IA)",
            body="Strong identification and authentication controls ensure that every user, device, and service accessing your systems is verified before being granted access. This is the gatekeeping function that makes access control effective.",
            bullets=[
                "Enforce unique identifiers for every user — no shared or generic accounts",
                "Implement multi-factor authentication for all network access to CUI systems",
                "Enforce password policies: minimum 12 characters, complexity requirements, 90-day rotation",
                "Implement account lockout after 5 consecutive failed login attempts",
                "Authenticate all devices before allowing network connection via 802.1X or certificate-based auth",
                "Store all passwords using FIPS 140-2 validated cryptographic modules",
            ],
            callout_box="MFA Requirement: IA.L2-3.5.3 mandates multi-factor authentication for network access. SMS-based MFA is acceptable but hardware tokens or authenticator apps are strongly recommended.",
        ),
        PDFSection(
            heading="Incident Response (IR)",
            body="Incident response capabilities ensure that when a security event occurs, your organization can detect it quickly, contain the damage, and recover while preserving evidence. CMMC requires not just a plan but demonstrated capability.",
            bullets=[
                "Develop and maintain an incident response plan with defined roles, responsibilities, and escalation procedures",
                "Conduct tabletop incident response exercises at least quarterly",
                "Establish relationships with external incident response resources before you need them",
                "Define and test communication procedures for notifying affected parties and the DIB-ISAC",
                "Implement automated incident detection capabilities (IDS/IPS, EDR, SIEM correlation rules)",
                "Maintain forensic investigation capability or retainer with a qualified forensics firm",
            ],
            callout_box="Test It: An untested incident response plan is as bad as no plan. Auditors will ask when your last exercise was and what you learned from it.",
        ),
        PDFSection(
            heading="Risk Assessment (RA)",
            body="Risk assessment is the process that ties all other domains together. It helps you understand your threat landscape, identify vulnerabilities, and prioritize your security investments where they'll have the greatest impact on protecting CUI.",
            bullets=[
                "Conduct a comprehensive risk assessment at least annually and after any significant infrastructure change",
                "Maintain a risk register that tracks identified risks, risk owners, and mitigation status",
                "Perform vulnerability scanning on all internet-facing systems at least monthly",
                "Perform vulnerability scanning on all internal systems at least quarterly",
                "Remediate critical vulnerabilities within 15 days and high-severity within 30 days",
                "Incorporate threat intelligence feeds relevant to the defense industrial base",
            ],
            callout_box="Priority: RA.L2-3.11.2 — Scan for vulnerabilities periodically and when new vulnerabilities are identified. Automated scanning is practically required to meet the cadence expectations.",
        ),
        PDFSection(
            heading="System and Communications Protection (SC)",
            body="System and communications protection controls secure the boundaries of your network and protect CUI during transmission. These controls prevent unauthorized data exfiltration and ensure the integrity of communications.",
            bullets=[
                "Implement boundary protection (firewalls, DMZ architecture) at all external and key internal network boundaries",
                "Encrypt all CUI in transit using FIPS 140-2 validated cryptography (TLS 1.2+ minimum)",
                "Encrypt all CUI at rest on mobile devices, removable media, and cloud storage",
                "Implement DNS filtering and web content filtering to block known malicious domains",
                "Segment networks to isolate CUI-processing systems from general-purpose systems",
                "Implement email security controls: SPF, DKIM, DMARC, and attachment sandboxing",
                "Monitor and control all data transfers across network boundaries",
            ],
            callout_box="Encryption Standard: FIPS 140-2 validation is required, not just FIPS 140-2 compliant. Verify your encryption modules are listed on the NIST CMVP validated modules list.",
        ),
    ],
    branding=NEXUS_BRANDING,
)

# ---------------------------------------------------------------------------
# PDF-2: Document Ad (LinkedIn Carousel)
# ---------------------------------------------------------------------------
DOCUMENT_AD = DocumentAdInput(
    slides=[
        Slide(
            headline="5 Signs Your Endpoint Security Is Failing",
            body="Is your organization truly protected — or just hoping for the best?",
        ),
        Slide(
            headline="You're Still Relying on Signature-Based AV",
            body="Traditional antivirus catches known threats. Modern attackers use fileless malware, living-off-the-land techniques, and zero-days that signatures will never detect.",
            stat_callout="68%",
            stat_label="of breaches involve techniques that bypass signature-based detection",
        ),
        Slide(
            headline="Alert Fatigue Has Taken Over",
            body="Your security team receives thousands of alerts per day but investigates fewer than 10%. Critical threats hide in the noise while analysts burn out.",
            stat_callout="4,000+",
            stat_label="average daily alerts per enterprise SOC",
        ),
        Slide(
            headline="Visibility Gaps Across Remote Endpoints",
            body="With hybrid work, 40% of your endpoints operate outside the corporate network. If you can't see them, you can't protect them — or prove compliance.",
            stat_callout="40%",
            stat_label="of endpoints operate outside the corporate perimeter",
        ),
        Slide(
            headline="Mean Time to Detect Keeps Climbing",
            body="Industry average detection time is 207 days. Every day an attacker lives in your environment, the cost and damage multiply exponentially.",
            stat_callout="207 days",
            stat_label="average dwell time before breach detection",
        ),
        Slide(
            headline="Get the Full Endpoint Security Assessment",
            body=None,
            is_cta_slide=True,
            cta_text="Download the free assessment at nexussecurity.com/endpoint",
        ),
    ],
    branding=NEXUS_BRANDING,
    aspect_ratio="1:1",
)
