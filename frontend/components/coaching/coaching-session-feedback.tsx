"use client";

import { useCallback, useMemo, useState } from "react";
import { useSWRConfig } from "swr";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { cn } from "@/lib/utils";
import {
  FEEDBACK_COMMENT_MAX_LEN,
  submitCoachingFeedback,
  type CoachingFeedbackPayload,
  type CoachingSession,
} from "@/lib/api";

const NEUTRAL = "\u2014";

type FeedbackValues = {
  feedback_rating: number | null;
  feedback_learned_new: boolean | null;
  feedback_comment: string | null;
};

function sessionToValues(session: CoachingSession): FeedbackValues {
  return {
    feedback_rating: session.feedback_rating,
    feedback_learned_new: session.feedback_learned_new,
    feedback_comment: session.feedback_comment,
  };
}

function hasAnyFeedbackInput(
  rating: number | null,
  learnedNew: boolean | null | undefined,
  comment: string,
): boolean {
  if (rating != null) return true;
  if (learnedNew !== null && learnedNew !== undefined) return true;
  return comment.trim().length > 0;
}

function formatRating(value: number | null): string {
  if (value == null) return NEUTRAL;
  return `${value} / 5`;
}

function formatLearned(value: boolean | null): string {
  if (value === null || value === undefined) return NEUTRAL;
  return value ? "Yes" : "No";
}

function formatComment(value: string | null): string {
  if (!value || !value.trim()) return NEUTRAL;
  return value;
}

function FeedbackRow({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground mb-1">{label}</p>
      <p className="text-white">{value}</p>
    </div>
  );
}

function ThanksView({ values }: { values: FeedbackValues }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Thanks for your feedback</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 text-sm">
        <FeedbackRow
          label="How useful was this analysis?"
          value={formatRating(values.feedback_rating)}
        />
        <FeedbackRow
          label="Did you learn something new about your trading behavior?"
          value={formatLearned(values.feedback_learned_new)}
        />
        <div>
          <p className="text-xs text-muted-foreground mb-1">Additional comments</p>
          <p className="text-white whitespace-pre-wrap">
            {formatComment(values.feedback_comment)}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

function StarRating({
  rating,
  onSelect,
  disabled,
}: {
  rating: number | null;
  onSelect: (value: number) => void;
  disabled: boolean;
}) {
  return (
    <div className="flex gap-1" role="group" aria-label="Rating 1 to 5">
      {[1, 2, 3, 4, 5].map((n) => (
        <button
          key={n}
          type="button"
          disabled={disabled}
          onClick={() => onSelect(n)}
          className={cn(
            "h-10 w-10 rounded-md border text-sm font-semibold transition-colors",
            rating === n
              ? "border-[var(--brand-gold,#d4a843)] bg-[var(--brand-gold,#d4a843)]/20 text-[var(--brand-gold,#d4a843)]"
              : "border-input bg-muted/30 text-muted-foreground hover:border-[var(--brand-gold,#d4a843)]/50",
            disabled && "pointer-events-none opacity-50",
          )}
          aria-pressed={rating === n}
          aria-label={`${n} out of 5`}
        >
          {n}
        </button>
      ))}
    </div>
  );
}

interface CoachingSessionFeedbackProps {
  sessionId: string;
  session: CoachingSession;
}

export function CoachingSessionFeedback({
  sessionId,
  session,
}: CoachingSessionFeedbackProps) {
  const { mutate } = useSWRConfig();
  const alreadySubmitted = Boolean(session.feedback_submitted_at);

  const [locked, setLocked] = useState(false);
  const [thanksValues, setThanksValues] = useState<FeedbackValues | null>(
    alreadySubmitted ? sessionToValues(session) : null,
  );
  const [rating, setRating] = useState<number | null>(null);
  const [learnedNew, setLearnedNew] = useState<boolean | null | undefined>(
    undefined,
  );
  const [comment, setComment] = useState("");
  const [emptyHint, setEmptyHint] = useState(false);
  const [submitError, setSubmitError] = useState("");

  const canSubmit = useMemo(
    () => hasAnyFeedbackInput(rating, learnedNew, comment),
    [rating, learnedNew, comment],
  );

  const buildPayload = useCallback((): CoachingFeedbackPayload => {
    const payload: CoachingFeedbackPayload = {};
    if (rating != null) payload.feedback_rating = rating;
    if (learnedNew !== null && learnedNew !== undefined) {
      payload.feedback_learned_new = learnedNew;
    }
    const trimmed = comment.trim();
    if (trimmed) payload.feedback_comment = trimmed;
    return payload;
  }, [rating, learnedNew, comment]);

  const handleSubmit = useCallback(async () => {
    if (locked || thanksValues) return;
    if (!canSubmit) {
      setEmptyHint(true);
      return;
    }
    setEmptyHint(false);
    setSubmitError("");
    setLocked(true);

    const payload = buildPayload();
    const snapshot: FeedbackValues = {
      feedback_rating: payload.feedback_rating ?? null,
      feedback_learned_new:
        payload.feedback_learned_new !== undefined
          ? payload.feedback_learned_new
          : null,
      feedback_comment: payload.feedback_comment ?? null,
    };

    try {
      await submitCoachingFeedback(sessionId, payload);
      setThanksValues(snapshot);
      await mutate(`/api/coaching/session/${sessionId}`);
    } catch (e: unknown) {
      setLocked(false);
      setSubmitError(
        e instanceof Error ? e.message : "Could not submit feedback",
      );
    }
  }, [
    locked,
    thanksValues,
    canSubmit,
    buildPayload,
    sessionId,
    mutate,
  ]);

  if (thanksValues) {
    return <ThanksView values={thanksValues} />;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Your feedback</CardTitle>
        <p className="text-sm text-muted-foreground">
          Help us improve your coaching experience. Answer any question you like.
        </p>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="space-y-2">
          <p className="text-sm font-medium">How useful was this analysis?</p>
          <StarRating
            rating={rating}
            onSelect={setRating}
            disabled={locked}
          />
        </div>

        <div className="space-y-2">
          <p className="text-sm font-medium">
            Did you learn something new about your trading behavior?
          </p>
          <div className="flex gap-2">
            <Button
              type="button"
              variant={learnedNew === true ? "default" : "outline"}
              size="sm"
              disabled={locked}
              onClick={() => setLearnedNew(true)}
            >
              Yes
            </Button>
            <Button
              type="button"
              variant={learnedNew === false ? "default" : "outline"}
              size="sm"
              disabled={locked}
              onClick={() => setLearnedNew(false)}
            >
              No
            </Button>
          </div>
        </div>

        <div className="space-y-2">
          <label
            htmlFor="coaching-feedback-comment"
            className="text-sm font-medium"
          >
            Additional comments (optional)
          </label>
          <textarea
            id="coaching-feedback-comment"
            value={comment}
            onChange={(e) =>
              setComment(e.target.value.slice(0, FEEDBACK_COMMENT_MAX_LEN))
            }
            disabled={locked}
            rows={4}
            maxLength={FEEDBACK_COMMENT_MAX_LEN}
            placeholder="What worked, what didn\u2019t, anything we should know\u2026"
            className={cn(
              "flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm",
              "ring-offset-background placeholder:text-muted-foreground",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
              "disabled:cursor-not-allowed disabled:opacity-50",
            )}
          />
          <p className="text-xs text-muted-foreground text-right">
            {comment.length} / {FEEDBACK_COMMENT_MAX_LEN}
          </p>
        </div>

        {emptyHint && (
          <p className="text-sm text-amber-400" role="status">
            Please answer at least one question before submitting.
          </p>
        )}
        {submitError && (
          <p className="text-sm text-red-400" role="alert">
            {submitError}
          </p>
        )}

        <Button
          type="button"
          disabled={locked || !canSubmit}
          onClick={() => void handleSubmit()}
        >
          {locked ? "Submitting\u2026" : "Submit feedback"}
        </Button>
      </CardContent>
    </Card>
  );
}
