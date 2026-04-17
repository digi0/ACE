const RESOURCES = [
  {
    category: "Mental Health & Wellness",
    items: [
      {
        name: "CAPS",
        full: "Counseling & Psychological Services",
        description:
          "Free, confidential counseling, crisis intervention, and mental health support for all Penn State students.",
        link: "https://studentaffairs.psu.edu/counseling",
      },
      {
        name: "Crisis Support",
        full: "988 Suicide & Crisis Lifeline",
        description:
          "24/7 crisis support — call or text 988 anytime. Crisis Text Line: text HOME to 741741.",
        link: "https://988lifeline.org/",
      },
      {
        name: "Peer Counseling",
        full: "CAPS Peer Counseling Program",
        description:
          "Student-run, confidential peer support program offering a safe space to talk through challenges.",
        link: "https://studentaffairs.psu.edu/counseling/services/peer-counseling",
      },
    ],
  },
  {
    category: "Medical & Health",
    items: [
      {
        name: "UHS",
        full: "University Health Services",
        description:
          "Primary medical care, immunizations, lab services, and preventive health resources on campus.",
        link: "https://studentaffairs.psu.edu/health",
      },
      {
        name: "Student Pharmacy",
        full: "UHS Student Pharmacy",
        description:
          "On-campus pharmacy offering prescription fills and over-the-counter medications at student-friendly prices.",
        link: "https://studentaffairs.psu.edu/health/services/pharmacy",
      },
    ],
  },
  {
    category: "Academic Support",
    items: [
      {
        name: "LRC",
        full: "Learning Resource Center",
        description:
          "Free tutoring, academic coaching, and supplemental instruction for Penn State courses.",
        link: "https://lrc.psu.edu/",
      },
      {
        name: "Writing Center",
        full: "Penn State Writing Center",
        description:
          "Free writing consultations for any stage — brainstorming, drafting, or final revisions.",
        link: "https://writing.psu.edu/",
      },
      {
        name: "Calc Central",
        full: "Calculus Central",
        description:
          "Drop-in help for calculus courses, staffed by graduate students and faculty instructors.",
        link: "https://math.psu.edu/undergraduate/calculus-central",
      },
      {
        name: "EECS Advising",
        full: "Engineering Advising Office",
        description:
          "Academic advising specific to CS and Engineering undergraduates at Penn State.",
        link: "https://www.eecs.psu.edu/students/undergraduate/advising/",
      },
    ],
  },
  {
    category: "Career & Professional",
    items: [
      {
        name: "Career Services",
        full: "Nittany Lion Career Network",
        description:
          "Resume reviews, mock interviews, career coaching, and on-campus recruiting events.",
        link: "https://careerservices.psu.edu/",
      },
      {
        name: "Handshake",
        full: "Handshake Job & Internship Portal",
        description:
          "PSU's official platform for finding internships, full-time jobs, and career events.",
        link: "https://psu.joinhandshake.com/",
      },
    ],
  },
  {
    category: "Campus Life",
    items: [
      {
        name: "OrgCentral",
        full: "Student Organizations Hub",
        description:
          "Browse and join 1,000+ student clubs, organizations, and interest groups at Penn State.",
        link: "https://orgcentral.psu.edu/",
      },
      {
        name: "RecSports",
        full: "Campus Recreation & Sports",
        description:
          "Fitness facilities, intramural sports, group fitness classes, and outdoor adventure programs.",
        link: "https://recsports.psu.edu/",
      },
      {
        name: "Student Activities",
        full: "Office of Student Activities",
        description:
          "Campus events, leadership opportunities, and programs to enrich your Penn State experience.",
        link: "https://studentaffairs.psu.edu/student-activities",
      },
    ],
  },
  {
    category: "Financial Support",
    items: [
      {
        name: "Bursar",
        full: "Bursar's Office",
        description:
          "Tuition billing, payment plans, and student account management for all Penn State students.",
        link: "https://bursar.psu.edu/",
      },
      {
        name: "Student Aid",
        full: "Office of Student Aid",
        description:
          "Scholarships, grants, loans, and work-study programs — explore all financial aid options.",
        link: "https://studentaid.psu.edu/",
      },
      {
        name: "Emergency Fund",
        full: "Student Emergency Aid Fund",
        description:
          "Short-term financial assistance for students facing unexpected hardship or crisis situations.",
        link: "https://studentaffairs.psu.edu/student-care/emergency-fund",
      },
    ],
  },
  {
    category: "Safety & Emergency",
    items: [
      {
        name: "UPPS",
        full: "University Police & Public Safety",
        description:
          "Campus law enforcement available 24/7. Emergency: 911. Non-emergency: (814) 863-1111.",
        link: "https://police.psu.edu/",
      },
      {
        name: "Safe Walk",
        full: "Safe Walk Escort Program",
        description:
          "Free nighttime walking escort service for students who feel unsafe on campus.",
        link: "https://police.psu.edu/services/safewalk",
      },
      {
        name: "Student Care",
        full: "Student Care & Advocacy",
        description:
          "Support for students facing personal crises, connecting them with the right university resources.",
        link: "https://studentaffairs.psu.edu/student-care",
      },
    ],
  },
];

/* ── Resource Card ──────────────────────────────────────────── */
function ResourceCard({ item }) {
  return (
    <div className="resource-card">
      <div className="resource-card-body">
        <div className="resource-card-header">
          <span className="resource-card-name">{item.name}</span>
          <span className="resource-card-full">{item.full}</span>
        </div>
        <p className="resource-card-desc">{item.description}</p>
      </div>
      <a
        className="resource-card-link"
        href={item.link}
        target="_blank"
        rel="noreferrer"
      >
        Visit →
      </a>
    </div>
  );
}

/* ── ResourceHub ────────────────────────────────────────────── */
export default function ResourceHub() {
  return (
    <div className="resource-hub">
      <div className="resource-hub-header">
        <h1 className="resource-hub-title">PSU Resource Hub</h1>
        <p className="resource-hub-subtitle">
          Everything Penn State has to offer — health, academics, career, campus life, and more.
          Click any card to visit the official PSU page.
        </p>
      </div>

      {RESOURCES.map((cat) => (
        <section key={cat.category} className="resource-section">
          <div className="resource-section-header">
            <h2 className="resource-section-title">{cat.category}</h2>
            <span className="resource-section-badge">
              {cat.items.length} resource{cat.items.length !== 1 ? "s" : ""}
            </span>
          </div>
          <div className="resource-grid">
            {cat.items.map((item) => (
              <ResourceCard key={item.name} item={item} />
            ))}
          </div>
        </section>
      ))}

      <p className="resource-hub-footer">
        These links redirect to official Penn State pages. ACE is not affiliated with or responsible for external content.
      </p>
    </div>
  );
}
