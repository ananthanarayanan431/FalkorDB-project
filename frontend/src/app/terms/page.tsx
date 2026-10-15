import type { Metadata } from "next";

import { LegalPage } from "@/components/legal";
import { contactLine, operatorName, site } from "@/lib/site";

export const metadata: Metadata = { title: "Terms and conditions" };

export default function Page() {
  return (
    <LegalPage title="Terms and conditions">
      <section>
        <p>
          These terms cover your use of {site.name}, operated by {operatorName}. By using the
          service you agree to them.
        </p>
      </section>

      <section>
        <h2>What the service is for</h2>
        <p>
          Recording what a departing employee knows about their work and building handover plans
          for the colleagues who take it over. Use it only for that purpose and only with the
          permission of your organisation.
        </p>
      </section>

      <section>
        <h2>What you may enter</h2>
        <ul>
          <li>Enter only information you are allowed to share inside your organisation.</li>
          <li>
            Do not enter passwords, keys or other secrets, or personal details about anyone that
            are not needed for the handover, such as health or financial information.
          </li>
          <li>Do not enter anything you know to be false.</li>
        </ul>
      </section>

      <section>
        <h2>Generated content</h2>
        <p>
          Interview questions, answer classifications, extracted items and plan summaries can be
          written by a language model and can be wrong or incomplete. Check a handover plan with
          the people involved before relying on it for decisions that matter.
        </p>
      </section>

      <section>
        <h2>Access</h2>
        <p>
          The service has no user accounts or sign-in. It must only be made available on a network
          where everyone who can reach it is allowed to see and change its data.
        </p>
      </section>

      <section>
        <h2>Availability and liability</h2>
        <p>
          The service is provided as it is. {operatorName.charAt(0).toUpperCase() + operatorName.slice(1)} does
          not promise that it will always be available or free of errors, and is not responsible
          for losses caused by relying on its content, to the extent the law allows.
        </p>
      </section>

      <section>
        <h2>Changes and questions</h2>
        <p>
          These terms may be updated; the current version is always on this page. For questions,{" "}
          {contactLine}.
        </p>
      </section>
    </LegalPage>
  );
}
