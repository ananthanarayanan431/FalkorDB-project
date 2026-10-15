import type { Metadata } from "next";

import { LegalPage } from "@/components/legal";
import { contactLine, operatorName, site } from "@/lib/site";

export const metadata: Metadata = { title: "Privacy policy" };

export default function Page() {
  return (
    <LegalPage title="Privacy policy">
      <section>
        <p>
          {site.name} is run by {operatorName}. This page explains what the service stores about
          you, why, where it goes and how to have it changed or removed.
        </p>
      </section>

      <section>
        <h2>What is stored</h2>
        <ul>
          <li>
            <strong>People:</strong> name, an ID, job role, seniority and whether you are leaving
            or staying.
          </li>
          <li>
            <strong>Work records:</strong> the systems, decisions and topics you worked on, the
            documents that cover them, how they relate, and how well colleagues know each of them.
            These come from imports by an administrator and from your own notes.
          </li>
          <li>
            <strong>Interview answers:</strong> the questions you were asked, your typed or
            transcribed answers, when you gave them, and whether an answer was skipped.
          </li>
          <li>
            <strong>Handover plans:</strong> the plans built for the people taking over your work,
            which include your interview answers.
          </li>
        </ul>
      </section>

      <section>
        <h2>Voice interviews</h2>
        <p>
          When you answer by voice, your microphone audio is sent to the server only while a voice
          session is open. It is passed to a speech recognition provider to be turned into text, and
          the agent&apos;s questions are turned into speech the same way. The service keeps the text
          of your answers. It does not store the audio recordings.
        </p>
      </section>

      <section>
        <h2>Why it is stored</h2>
        <p>
          To keep knowledge that only you hold from being lost when you leave, and to give each
          colleague a handover plan that fits what they already know. The service does not use it
          for anything else.
        </p>
      </section>

      <section>
        <h2>Third parties</h2>
        <p>
          If a language model is configured, interview questions, your answers and notes, and plan
          summaries are processed through OpenRouter and the model provider it routes to. Voice
          audio is processed through OpenRouter by the configured speech provider (Deepgram by
          default). Their own privacy terms apply to that processing. The service sends your data
          to no other third parties.
        </p>
      </section>

      <section>
        <h2>Cookies and tracking</h2>
        <p>
          The service sets no cookies and uses no analytics or advertising trackers. Your browser
          keeps two small preferences in local storage: which leaver you selected and the last
          interview you opened. You can clear them on the Settings page.
        </p>
      </section>

      <section>
        <h2>How long it is kept</h2>
        <p>
          Records are kept until an administrator deletes them. Saved handover plans keep a copy of
          the answers they include, so they stay as they were when given.
        </p>
      </section>

      <section>
        <h2>Your choices</h2>
        <p>
          You can skip any interview question. To see, correct or delete what is stored about you,{" "}
          {contactLine}.
        </p>
      </section>

      <section>
        <h2>Changes</h2>
        <p>If this policy changes, the new version is published on this page with its effective date.</p>
      </section>
    </LegalPage>
  );
}
