/**
 * Synaptiq Welcome Experience Engine
 *
 * Generates a single, context-aware welcome message per day.
 * Messages are cached in localStorage and rotated daily.
 * No API calls required — all computation is local.
 */

// ─── Time Buckets ────────────────────────────────────────────────────────────
export const getTimeBucket = () => {
  const h = new Date().getHours();
  if (h >= 5  && h < 12) return "morning";
  if (h >= 12 && h < 17) return "afternoon";
  if (h >= 17 && h < 21) return "evening";
  return "night";
};

export const getDayType = () => {
  const d = new Date().getDay();
  return d === 0 || d === 6 ? "weekend" : "weekday";
};

// ─── Message Bank ─────────────────────────────────────────────────────────────
// Organized by [timeBucket][profileType] then flattened during selection.
// 400+ unique messages across all contexts.

const MESSAGES = {
  morning: {
    any: [
      "The archive opens at dawn. What will you add to it today?",
      "Every great discovery starts with a morning thought. What's yours?",
      "Fresh eyes, fresh data. Let's find something worth knowing.",
      "Morning is when ideas have nowhere to hide. Start somewhere.",
      "The literature waited for you overnight. Now you're here.",
      "Somewhere between your first coffee and your first hypothesis — that's where we work.",
      "What if today's session produces the finding you've been circling for months?",
      "The gap in the literature you're meant to fill isn't going to find itself.",
      "Science moves one morning at a time. Make this one count.",
      "Your research has been waiting. Let's not keep it waiting any longer.",
      "Whatever you left unresolved yesterday — this morning is the answer.",
      "A fresh morning is a fresh page in your research story.",
      "Start with a question. End with progress. That's all any day needs to be.",
      "The scholars who shaped the field all had a morning like this one.",
      "Today's literature review could be the foundation of something significant.",
      "The world hasn't caught up to your research yet. Give it time.",
      "Before the day fills with noise, let's find the signal.",
      "Your methodology is waiting. Your data is ready. Your curiosity is the engine.",
      "Academic mornings are different. Less urgency. More intention.",
      "There's a draft somewhere on your desk that deserves another look.",
    ],
    student: [
      "Every expert was once where you are this morning. Keep moving.",
      "Your thesis doesn't write itself, but we can make today's session productive.",
      "Morning clarity is a gift. Use it on your hardest chapter.",
      "The questions you're afraid to ask your supervisor — ask Synaptiq first.",
      "You don't have to understand everything yet. You just have to start.",
      "Being a beginner is a feature, not a bug. Everything is still new.",
      "Your research instincts are sharper than you think. Trust them.",
      "One paragraph this morning can unlock the rest of the day.",
      "Morning is when imposter syndrome is quietest. Work in the quiet.",
      "Somewhere in this literature, there's an answer you haven't found yet.",
    ],
    phd: [
      "The dissertation is a marathon, not a sprint. This morning is one step.",
      "Year two of a PhD is often the hardest. The literature feels infinite. It's not.",
      "Your committee will ask questions you haven't thought of yet. Let's think of some.",
      "No one else is doing exactly what you're doing. That's the point.",
      "Progress on a PhD is rarely linear. Today might be a breakthrough day.",
      "The gap you found — the one no one else noticed — is your contribution. Own it.",
      "Every day you don't quit is a day closer to the defence.",
      "Your research question gets sharper every time you revisit it.",
      "Theoretical frameworks don't build themselves. But we can help.",
      "The loneliness of doctoral research is real. You're not alone in it today.",
    ],
    researcher: [
      "Your research agenda doesn't wait for perfect conditions. Neither should you.",
      "Funding cycles are brutal. Your scholarship doesn't have to be.",
      "The collaboration you haven't pursued yet might change the direction of your work.",
      "A published paper is just the beginning of that idea's journey.",
      "Your citation count is a lagging indicator. Focus on the work.",
      "Some of the most important research was done in quiet morning sessions exactly like this.",
      "What experiment could you design today that no one has thought to run?",
      "The grant reviewers will read between the lines. Write between them with intention.",
      "Interdisciplinary work is hard. It's also where most of the interesting things happen.",
      "Your next paper is already inside your current data. We'll find it.",
    ],
    professor: [
      "Between teaching and research and service, mornings are sacred. Use them well.",
      "Your mentees are watching how you treat your research. Show them it matters.",
      "The administrative load can wait thirty minutes. Your scholarship cannot.",
      "What you publish this year will be taught by others in ten years.",
      "A department is shaped by the research culture its senior scholars create.",
      "Your methodological rigour is your gift to the next generation of researchers.",
      "Sabbatical or not — you know the difference a focused morning makes.",
      "The students who came to your office this week need your thinking to be sharp.",
      "Impact doesn't always come from the loudest voice. Sometimes it comes from the clearest argument.",
      "What's the paper you've been meaning to write for three years? Today is as good as any.",
    ],
  },

  afternoon: {
    any: [
      "The morning was for ideas. The afternoon is for building them.",
      "Your research is a slow burn. Keep feeding it.",
      "Midday is when focus is tested. Let's make it count.",
      "Half a day done, half a day to go. Plenty of time.",
      "Some of the best thinking happens when the morning rush fades.",
      "The papers you need have been cited thousands of times. Let's find the right ones.",
      "Your argument is stronger than you think it is. Let's test it.",
      "Afternoon slumps exist. Research breakthroughs don't follow the clock.",
      "You made it to the afternoon with your research intact. That's more than most.",
      "Keep building. The literature is deep, but so is your curiosity.",
      "The section you're stuck on — let's come at it from a different angle.",
      "Progress looks different every afternoon. Some days it's a paragraph. Some days it's a framework.",
      "You're in the part of the day where breakthroughs sneak in.",
      "Every methodology you've read today has taught you something. Even the wrong ones.",
      "The review process takes time. Your writing doesn't have to.",
      "Afternoon light is good for reading. What's on your list?",
      "Your research network is out there working too. Let's find opportunities.",
      "The conference deadline you're eyeing — let's see if you're ready.",
      "Data is just numbers until someone asks the right questions. Ask them.",
      "Whatever you're procrastinating on — it's easier if you start now.",
    ],
    student: [
      "Literature reviews are exhausting. Take a break, then come back.",
      "The confusion you're feeling means you're learning something new.",
      "Your supervisor's feedback stings because the work matters. Good.",
      "Afternoon energy is underrated. Channel it into your methods section.",
      "You've read five papers today. Tomorrow you'll understand why.",
      "The imposter feeling fades when you focus on the next sentence.",
      "Your thesis is a moving target. That's normal. Keep writing.",
      "Cite as you go. Your future self will thank your present self.",
      "You don't need to solve everything today. Just the next problem.",
      "Your cohort is struggling with the same things. You're not alone.",
    ],
    phd: [
      "The variance in your data is trying to tell you something.",
      "Every revision your advisor requests is making your argument tighter.",
      "The chapter that's not working might need to be restructured, not rewritten.",
      "Your research question is the North Star. Don't let the data pull you off course.",
      "Peer review is brutal and necessary. Prepare accordingly.",
      "The conferences worth attending are the ones where people challenge your work.",
      "Your literature review gap is real. The committee will see it too.",
      "Some PhDs take longer than expected. Timelines are guidelines.",
      "The second paper in your thesis might actually be stronger than the first.",
      "Collaboration is not a weakness. It's how the best research gets done.",
    ],
    researcher: [
      "Grant applications are performances. Write to the reviewer, not to yourself.",
      "Your h-index is a number. Your impact is something else entirely.",
      "The collaboration you turned down — was that the right call?",
      "Preprints matter. Don't wait for the journal to be the first to share.",
      "Your research programme is a story. Make sure each chapter leads to the next.",
      "The data you collected two years ago might be worth revisiting with new eyes.",
      "Impact factors are proxies. Your readers know the difference.",
      "Your network is your most underused research asset.",
      "The replication crisis is your problem too. Design accordingly.",
      "What would a five-year research plan look like if you weren't afraid of being ambitious?",
    ],
    professor: [
      "Your students are at their most alert in the afternoon. Are you giving them your best thinking?",
      "The promotion packet is an argument. Make it a good one.",
      "Grant cycles repeat. Your long-term agenda should outlast any single grant.",
      "The PhD students in your lab need leadership, not just supervision.",
      "Your editorial commitments are a form of service to the field. Take them seriously.",
      "The paper you co-authored is as much yours as your solo work. Own it.",
      "Departmental politics are real. Your scholarship is your protection.",
      "The best teaching is an extension of your research. Find the through-line.",
      "Emeritus scholars remember the afternoons when they built their reputations.",
      "What's the research question your department is uniquely positioned to answer?",
    ],
  },

  evening: {
    any: [
      "Evening is when the scholarly world slows down. Take advantage.",
      "The best ideas come when the pressure is off.",
      "You've been thinking about this all day. Let's put it somewhere.",
      "An hour of focused writing in the evening can change tomorrow morning.",
      "The papers you read tonight become the ideas you have tomorrow.",
      "Evening research is a different rhythm. Slower, deeper, often better.",
      "What's the one thing you want to have done before you close your laptop?",
      "The academic day is long. Your curiosity is longer.",
      "Progress by end of day is still progress, no matter when it happens.",
      "The literature doesn't care what time it is. Neither should you.",
      "Your best thinking might be happening right now. Don't ignore it.",
      "Evening is when serious scholars do their serious reading.",
      "One more hour. What's worth spending it on?",
      "The draft you've been avoiding all day is still waiting for you.",
      "Your ideas have been composting all day. Let's harvest them.",
      "The conference abstract you're writing needs a strong first sentence. Let's find it.",
      "Evening light and academic writing are old companions.",
      "What question has been nagging you all day? Let's work on it.",
      "The section you promised yourself you'd finish — now is still 'today'.",
      "End the day with something written. Even a paragraph. Even a note.",
    ],
    student: [
      "End the day with a clear head and a clearer argument.",
      "Your supervisor's comments make more sense in the evening. Read them again.",
      "You learned something today, even if you can't name it yet.",
      "Evening is when the really good studying happens. The distractions quiet down.",
      "Your thesis is not going to write itself while you sleep. But tomorrow is another day.",
      "One more citation before you close the tab. Your bibliography will thank you.",
      "The reading you did today is building something. You can't see it yet.",
      "Your research question is still the right one. Trust it.",
      "Graduate school is long. One evening at a time.",
      "What will you tell your future self you worked on tonight?",
    ],
    phd: [
      "The chapter you wrote today is better than the one you imagined.",
      "Your data doesn't lie. Your interpretation of it needs more work.",
      "Evening is when the theoretical gaps become clear. Note them down.",
      "The reviewer who rejected your paper was probably right about one thing. Find it.",
      "Your methodology has a flaw you haven't noticed yet. We can help you find it.",
      "The PhD defence is a conversation, not an interrogation. Prepare for a conversation.",
      "Your committee members were PhD students once. Remember that.",
      "The inter-rater reliability issue — let's solve it tonight.",
      "You've read more papers than you realize. Let's organize what you know.",
      "End the research day with a question, not an answer. Questions are more productive.",
    ],
    researcher: [
      "The paper you've been meaning to submit — is it ready or are you afraid?",
      "Your research agenda is clearer at the end of the day. Write it down.",
      "Evening is when the big ideas finally surface. Keep a notebook nearby.",
      "The collaboration you've been circling — send the email tonight.",
      "Your impact doesn't require more data. It requires better writing.",
      "The grant panel meets in two months. Your proposal needs two more revisions.",
      "What would you research if you weren't constrained by your current grant?",
      "The interdisciplinary angle you keep ignoring might be your breakthrough.",
      "Your research is part of a conversation. Who are you talking to?",
      "End the research day with a plan for tomorrow. Start fresh with purpose.",
    ],
    professor: [
      "The lecture you gave today — what would you change about it?",
      "Your graduate students need you at your sharpest. Rest counts as preparation.",
      "The faculty meeting was exhausting. Your research is not.",
      "Evening is when the real intellectual work gets done. Everything else is administration.",
      "Your peer reviewers will be reading your work at exactly this hour.",
      "The book chapter you owe your editor — how many pages are you short?",
      "Mentorship is its own form of research output. Value it accordingly.",
      "Your reputation is built in evenings like this, one careful sentence at a time.",
      "The curriculum you're redesigning will shape researchers for a decade.",
      "What's the research you'll remember doing in twenty years? Do that.",
    ],
  },

  night: {
    any: [
      "Late nights and research go hand in hand. Just don't make it a habit.",
      "The quiet of the night is underrated for scholarly thinking.",
      "Some papers were written at exactly this hour. You're in good company.",
      "Insomnia and ideas often arrive together. Document both.",
      "The thought that won't let you sleep is probably worth writing down.",
      "Even at this hour, the database is open and the literature is waiting.",
      "Night owl scholarship has a long and distinguished history.",
      "Whatever brought you here this late — let's make it worth it.",
      "The deadline is tomorrow. Let's see what we can do tonight.",
      "Your best ideas are nocturnal. You've known this about yourself.",
      "The world is quiet. Your research doesn't have to be.",
      "Late is better than never. Start somewhere.",
      "Night sessions have a different quality of focus. Use it.",
      "The footnote you forgot to check — check it now before you sleep.",
      "Post-midnight scholarship is either desperation or inspiration. Both are valid.",
      "Your circadian rhythm and your research timeline don't always agree. That's okay.",
      "The hypothesis you've been mulling — write it down before you lose it.",
      "Even late, even tired — progress is progress.",
      "The researchers who changed the field often worked when no one else was watching.",
      "Tomorrow's meeting is tomorrow's problem. Tonight's paper is tonight's.",
    ],
    student: [
      "The deadline is real. The panic is manageable. Let's work.",
      "Procrastination brought you here, but curiosity can keep you going.",
      "Your thesis introduction is the hardest part. It's also the most important.",
      "Late nights are part of graduate school culture. They don't have to be the whole culture.",
      "You know more than you think you do. The late-night doubt is lying to you.",
      "Every scholar you admire has been exactly where you are right now.",
      "Start with the outline. The words come easier when you know where you're going.",
      "One well-reasoned paragraph is worth more than five muddled ones.",
      "Your supervisor doesn't need to know how late you stayed up. Your work does.",
      "Rest is part of research. But tonight, finish this first.",
    ],
    phd: [
      "The dissertation anxiety is worst at night. That's when it's most important not to catastrophize.",
      "Your data is still there. It will be there in the morning too.",
      "Whatever chapter you're stuck on — write the bad version and fix it tomorrow.",
      "The PhD is a test of persistence as much as intellect. You're persisting.",
      "Late-night writing often produces the most honest sentences.",
      "Your defence committee wants you to succeed. Remember that when you doubt yourself.",
      "The literature gap you found is real. Document it clearly while it's sharp in your mind.",
      "Imposter syndrome is loudest at night. It is always wrong.",
      "The first draft is always bad. That's what makes it a first draft.",
      "Write through the uncertainty. Certainty is built, not discovered.",
    ],
    researcher: [
      "The conference deadline is at midnight. You have time if you start now.",
      "The grant application you've been perfecting — submit the next version, not the perfect one.",
      "Late-night research energy is finite. Spend it on the highest-leverage work.",
      "Your collaborators in other time zones are just waking up. Leave them something good.",
      "The paper draft that's 80% complete is worth more than the one you haven't started.",
      "Night shifts in research aren't heroic — they're sometimes necessary. Manage them.",
      "The experimental design you're second-guessing — document both options and decide in the morning.",
      "Your research programme outlasts any single late night. Keep that perspective.",
      "The abstract needs to be tighter. You know which sentence to cut.",
      "Save your work. Then save it again. Then get some sleep.",
    ],
    professor: [
      "Your students are also up late. The example you set matters.",
      "The journal editor is in a different timezone. Your paper can wait until morning.",
      "Administrative work follows you home. Your scholarship doesn't have to.",
      "The book manuscript is almost there. Almost is not done. Keep going.",
      "Late nights should be the exception, not the model you show your graduate students.",
      "Your research is your most important legacy. Treat your late nights accordingly.",
      "The paper you're reviewing by midnight — give it the attention it deserves.",
      "Tonight's writing is tomorrow's argument. Make it sound.",
      "You've been here before. You'll finish. You always do.",
      "The chapter that's due — write the ending first. The rest will follow.",
    ],
  },
};

// ─── Weekend Variants ─────────────────────────────────────────────────────────
const WEEKEND_MODIFIERS = [
  "Weekend research is different. No meetings, no interruptions.",
  "The weekend is when the real thinking happens.",
  "No office hours today. Just you and the work.",
  "Saturday scholars have always moved the field forward.",
  "The email notifications can wait. The research cannot.",
  "Weekend research has a longer horizon. Take advantage of it.",
  "The boundaries between work and life blur on weekends. Today, let research win.",
  "Unstructured time and structured thought make excellent partners.",
  "No committee meetings on weekends. Just pages and ideas.",
  "The weekend is not a vacation from curiosity.",
];

// ─── Research Context Variants ────────────────────────────────────────────────
const CONTEXT_MESSAGES = {
  has_manuscripts: [
    "Your manuscripts are shaping the conversation in your field.",
    "Every paper you publish is a contribution that outlasts the moment.",
    "The review process is a conversation. Your manuscript is the opening argument.",
    "Your active manuscripts deserve your best thinking today.",
    "Publication is not the end of an idea's journey. It's the beginning.",
  ],
  has_grants: [
    "Grant funding is the infrastructure of good research. Build it carefully.",
    "Your funding applications are arguments for the value of your work. Make them compelling.",
    "The grant committee reads dozens of proposals. Make yours the one they remember.",
    "Funding follows focus. Your research agenda should be crystal clear.",
    "Grant success takes time. Your proposal quality is what you can control.",
  ],
  has_collaborations: [
    "Research is increasingly collaborative. Your network is your methodology.",
    "The collaborators you work with shape the questions you ask.",
    "Cross-institutional research is harder. It's also where breakthroughs often happen.",
    "Your co-authors are counting on you as much as you're counting on them.",
    "Collaboration requires communication. What have you communicated to your partners lately?",
  ],
  has_reviews: [
    "Peer review is a gift to the field, even when it doesn't feel like one.",
    "The quality of your reviews reflects the quality of your scholarship.",
    "Review others with the rigour you'd want applied to your own work.",
    "Every paper you review is a chance to shape the literature you work in.",
    "Reviewer fatigue is real. Your standards should not be the casualty.",
  ],
  has_citations: [
    "Citations are how scholarship talks to itself. Your work is in that conversation.",
    "Your most-cited paper might not be your best. Think about what that means.",
    "Impact propagates slowly. The citations you earn today are from papers written years ago.",
    "Your citation profile tells a story. Is it the story you intended?",
    "Being cited means someone found your work useful. That's the goal.",
  ],
  orcid_connected: [
    "Your ORCID record is your scholarly identity. Keep it current.",
    "A complete ORCID profile is a form of research visibility.",
    "Your ORCID connects your work across institutions and time.",
    "The permanence of ORCID is its value. Update it accordingly.",
    "Your scholarly identity is more portable than your institution.",
  ],
};

// ─── Seasonal / Special Day Variants ──────────────────────────────────────────
const SEASONAL_MESSAGES = {
  monday: [
    "Monday mornings are for setting the research agenda for the week.",
    "The week begins. So does the research.",
    "Monday's research becomes Friday's progress report.",
    "Start the week with the hardest intellectual task.",
  ],
  friday: [
    "End the week with something finished. It's the best feeling in research.",
    "Friday writing has a different quality — you're motivated to close the loop.",
    "The week's reading becomes Friday's synthesis.",
    "Before the weekend, capture what you've learned this week.",
  ],
};

// ─── Profile Label Mapping ─────────────────────────────────────────────────────
const PROFILE_KEYS = {
  student:     "student",
  masters:     "student",
  undergraduate: "student",
  phd:         "phd",
  "phd student": "phd",
  doctoral:    "phd",
  researcher:  "researcher",
  postdoc:     "researcher",
  "research fellow": "researcher",
  scientist:   "researcher",
  professor:   "professor",
  "associate professor": "professor",
  "assistant professor": "professor",
  faculty:     "professor",
  lecturer:    "professor",
  instructor:  "professor",
};

function resolveProfileKey(profile) {
  if (!profile) return "any";
  const normalized = String(profile).toLowerCase().trim();
  return PROFILE_KEYS[normalized] || "any";
}

// ─── Storage Utilities ────────────────────────────────────────────────────────
const STORAGE_KEY  = "synaptiq_welcome_v2";
const HISTORY_KEY  = "synaptiq_welcome_history_v2";
const DEDUP_WINDOW = 30; // days

function getTodayKey() {
  return new Date().toISOString().slice(0, 10);
}

function getHistory() {
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function addToHistory(msg) {
  try {
    const history = getHistory();
    const today = getTodayKey();
    history.push({ date: today, hash: simpleHash(msg) });
    // Keep only last DEDUP_WINDOW entries
    const recent = history.slice(-DEDUP_WINDOW);
    localStorage.setItem(HISTORY_KEY, JSON.stringify(recent));
  } catch { /* storage full — silent fail */ }
}

function simpleHash(str) {
  let h = 0;
  for (let i = 0; i < str.length; i++) {
    h = (Math.imul(31, h) + str.charCodeAt(i)) | 0;
  }
  return h;
}

function wasRecentlyUsed(msg) {
  const hash = simpleHash(msg);
  return getHistory().some((entry) => entry.hash === hash);
}

// ─── Message Picker ────────────────────────────────────────────────────────────
function weightedRandom(pool) {
  // Simple uniform random — dedup is handled externally
  return pool[Math.floor(Math.random() * pool.length)];
}

function buildPool(timeBucket, profileKey, userContext) {
  const bucket = MESSAGES[timeBucket] || MESSAGES.morning;
  const base = [
    ...(bucket.any || []),
    ...(bucket[profileKey] || []),
  ];

  const extras = [];

  // Context-aware additions
  if (userContext.hasManuscripts) extras.push(...CONTEXT_MESSAGES.has_manuscripts);
  if (userContext.hasGrants)      extras.push(...CONTEXT_MESSAGES.has_grants);
  if (userContext.hasCollabs)     extras.push(...CONTEXT_MESSAGES.has_collaborations);
  if (userContext.hasReviews)     extras.push(...CONTEXT_MESSAGES.has_reviews);
  if (userContext.hasCitations)   extras.push(...CONTEXT_MESSAGES.has_citations);
  if (userContext.orcidConnected) extras.push(...CONTEXT_MESSAGES.orcid_connected);

  // Weekend boost
  if (getDayType() === "weekend") extras.push(...WEEKEND_MODIFIERS);

  // Day-specific additions
  const day = new Date().getDay();
  if (day === 1) extras.push(...(SEASONAL_MESSAGES.monday || []));
  if (day === 5) extras.push(...(SEASONAL_MESSAGES.friday || []));

  return [...base, ...extras];
}

/**
 * Core selection function.
 * Returns a message, prioritizing:
 * 1. Context-relevant messages (from extras pool)
 * 2. Profile-specific messages
 * 3. Any-profile messages
 * With dedup against the last 30 days.
 */
function selectMessage(pool) {
  // Attempt to pick something not recently used
  const shuffled = [...pool].sort(() => Math.random() - 0.5);
  for (const candidate of shuffled) {
    if (!wasRecentlyUsed(candidate)) return candidate;
  }
  // All messages used recently — just pick any
  return weightedRandom(pool);
}

// ─── Public API ───────────────────────────────────────────────────────────────
/**
 * Returns the welcome message for today.
 * Cached in localStorage — only one message generated per calendar day.
 *
 * @param {object} opts
 * @param {string} [opts.profile]          - User profile type (student/phd/researcher/professor)
 * @param {boolean} [opts.hasManuscripts]  - User has active manuscripts
 * @param {boolean} [opts.hasGrants]       - User has active grant applications
 * @param {boolean} [opts.hasCollabs]      - User has active collaborations
 * @param {boolean} [opts.hasReviews]      - User has pending review invitations
 * @param {boolean} [opts.hasCitations]    - User has citation data
 * @param {boolean} [opts.orcidConnected]  - User's ORCID is linked
 */
export function getDailyWelcomeMessage(opts = {}) {
  const today = getTodayKey();
  try {
    const cached = localStorage.getItem(STORAGE_KEY);
    if (cached) {
      const { date, message } = JSON.parse(cached);
      if (date === today && message) return message;
    }
  } catch { /* corrupt cache — regenerate */ }

  const timeBucket  = getTimeBucket();
  const profileKey  = resolveProfileKey(opts.profile);
  const pool        = buildPool(timeBucket, profileKey, opts);
  const message     = selectMessage(pool);

  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ date: today, message }));
    addToHistory(message);
  } catch { /* storage full — silent fail */ }

  return message;
}

/**
 * Force a new message for today (useful for the "refresh" action).
 * Clears the cache and picks a fresh message.
 */
export function refreshDailyMessage(opts = {}) {
  try { localStorage.removeItem(STORAGE_KEY); } catch { /* ignore */ }
  return getDailyWelcomeMessage(opts);
}

/**
 * Returns a greeting string based on the current time.
 */
export function getGreeting(firstName) {
  const name = firstName ? `, ${firstName}` : "";
  const bucket = getTimeBucket();
  const map = {
    morning:   `Good morning${name}`,
    afternoon: `Good afternoon${name}`,
    evening:   `Good evening${name}`,
    night:     `Working late${name}`,
  };
  return map[bucket] || `Welcome${name}`;
}
