// Details shown on the privacy policy and terms pages. Fill these in for your
// organisation before going live; the pages fall back to generic wording while
// they are empty.
export const site = {
  name: "Knowledge Transfer",
  /** Legal name of the organisation that operates this deployment. */
  operator: process.env.NEXT_PUBLIC_OPERATOR_NAME ?? "",
  /** Where people send privacy questions and data requests. */
  contactEmail: process.env.NEXT_PUBLIC_CONTACT_EMAIL ?? "",
  /** Date the current policy and terms took effect, as YYYY-MM-DD. */
  policyDate: process.env.NEXT_PUBLIC_POLICY_DATE ?? "",
};

export const operatorName = site.operator || "the organisation that runs this service";
export const contactLine = site.contactEmail
  ? `email ${site.contactEmail}`
  : "contact the administrator of this service";
