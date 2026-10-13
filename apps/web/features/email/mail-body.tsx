"use client";

import DOMPurify from "dompurify";
import { ImageIcon } from "lucide-react";
import { useMemo, useRef, useState } from "react";

import { Button } from "@/components/ui/button";

// Remote pictures (and tracking pixels) load only after "Show images".
function page(html: string, images: boolean) {
  // Mail layouts often keep their CSS in <head>; keep those <style> blocks (the CSP below still blocks loads).
  const parsed = new DOMParser().parseFromString(html, "text/html");
  const styles = [...parsed.querySelectorAll("style")]
    .map((style) => (style.textContent ?? "").replace(/<\/style/gi, ""))
    .join("\n");
  const clean = DOMPurify.sanitize(parsed.body.innerHTML, {
    WHOLE_DOCUMENT: false,
    ADD_TAGS: ["style"],
    FORBID_TAGS: ["form", "input", "button", "iframe", "object", "embed"],
    FORBID_ATTR: ["srcset"],
  });
  const imageSources = images ? "https: http: data:" : "data:";
  return `<!doctype html><html><head><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src ${imageSources}; style-src 'unsafe-inline'; font-src data:">
<base target="_blank">
<style>body{margin:0;padding:16px;font:15px/1.6 system-ui,sans-serif;color:#18181b;background:#fff;overflow-wrap:anywhere}
img{max-width:100%;height:auto}table{max-width:100%}a{color:#be123c}</style><style>${styles}</style></head><body>${clean}</body></html>`;
}

// One email's HTML: its real layout, no scripts, no forms, links open in a new tab.
export default function MailBody({ html, text }: { html: string; text: string }) {
  const frame = useRef<HTMLIFrameElement>(null);
  const [images, setImages] = useState(false);
  const [height, setHeight] = useState(240);
  const hasImages = /<img\b|background(-image)?\s*[:=]/i.test(html);
  const srcDoc = useMemo(() => (html ? page(html, images) : ""), [html, images]);

  if (!html) {
    return (
      <div className="max-w-prose whitespace-pre-wrap break-words text-[15px] leading-7">
        {text || <span className="text-muted-foreground">(no text)</span>}
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {hasImages && !images && (
        <div className="flex items-center gap-2 rounded-lg border border-border bg-muted/50 px-3 py-2 text-sm">
          <ImageIcon className="size-4 text-muted-foreground" aria-hidden="true" />
          <span className="mr-auto text-muted-foreground">Images are hidden.</span>
          <Button size="sm" variant="outline" onClick={() => setImages(true)}>
            Show images
          </Button>
        </div>
      )}
      <iframe
        ref={frame}
        title="Email"
        srcDoc={srcDoc}
        // No allow-scripts: nothing in the mail can run. Same-origin only lets Venus read its height.
        sandbox="allow-same-origin allow-popups allow-popups-to-escape-sandbox"
        referrerPolicy="no-referrer"
        className="w-full rounded-lg border border-border bg-white"
        style={{ height }}
        onLoad={() => {
          const body = frame.current?.contentDocument?.body;
          if (body) setHeight(Math.min(Math.max(body.scrollHeight + 4, 120), 4000));
        }}
      />
    </div>
  );
}
