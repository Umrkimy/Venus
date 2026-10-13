// Says up front that this is the portfolio demo, not someone's real Venus.
export default function DemoBanner() {
  return (
    <p className="ml-2 truncate rounded-full bg-background/50 px-3 py-1 text-xs text-muted-foreground backdrop-blur-md">
      Demo: runs only in your browser, nothing touches a real PC.{" "}
      <a
        href="https://github.com/Umrkimy/Venus"
        target="_blank"
        rel="noreferrer"
        className="underline underline-offset-2 hover:text-foreground"
      >
        Code on GitHub
      </a>
    </p>
  );
}
