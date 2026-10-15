import { ButtonLink, EmptyState } from "@/components/ui";

export default function NotFound() {
  return (
    <EmptyState title="Page not found" action={<ButtonLink href="/">Go to the overview</ButtonLink>}>
      There is no page at this address.
    </EmptyState>
  );
}
