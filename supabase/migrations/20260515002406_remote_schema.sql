drop extension if exists "pg_net";

alter table "public"."trades" drop constraint "trades_account_id_fkey";

alter table "public"."trades" drop constraint "trades_source_check";


  create table "public"."coaching_sessions" (
    "id" uuid not null default gen_random_uuid(),
    "user_id" uuid not null,
    "account_id" uuid not null,
    "created_at" timestamp with time zone default now(),
    "period_from" timestamp with time zone,
    "period_to" timestamp with time zone,
    "metrics_snapshot" jsonb,
    "rag_context" jsonb,
    "recommendations" jsonb,
    "ai_response" text,
    "verdict" text,
    "new_trades_count" integer,
    "model_used" text,
    "main_problem" text
      );


alter table "public"."coaching_sessions" enable row level security;


  create table "public"."news" (
    "id" uuid not null default gen_random_uuid(),
    "date" timestamp with time zone not null,
    "headline" text not null,
    "summary" text,
    "source" text,
    "url" text,
    "category" text,
    "matched_instruments" text[] default '{}'::text[],
    "created_at" timestamp with time zone default now()
      );


alter table "public"."news" enable row level security;

CREATE UNIQUE INDEX coaching_sessions_pkey ON public.coaching_sessions USING btree (id);

CREATE INDEX idx_coaching_account ON public.coaching_sessions USING btree (account_id);

CREATE INDEX idx_coaching_user ON public.coaching_sessions USING btree (user_id);

CREATE INDEX idx_news_date ON public.news USING btree (date);

CREATE INDEX idx_news_instruments ON public.news USING gin (matched_instruments);

CREATE UNIQUE INDEX news_pkey ON public.news USING btree (id);

alter table "public"."coaching_sessions" add constraint "coaching_sessions_pkey" PRIMARY KEY using index "coaching_sessions_pkey";

alter table "public"."news" add constraint "news_pkey" PRIMARY KEY using index "news_pkey";

alter table "public"."coaching_sessions" add constraint "coaching_sessions_account_id_fkey" FOREIGN KEY (account_id) REFERENCES public.accounts(id) ON DELETE CASCADE not valid;

alter table "public"."coaching_sessions" validate constraint "coaching_sessions_account_id_fkey";

alter table "public"."coaching_sessions" add constraint "coaching_sessions_user_id_fkey" FOREIGN KEY (user_id) REFERENCES public.users(id) not valid;

alter table "public"."coaching_sessions" validate constraint "coaching_sessions_user_id_fkey";

alter table "public"."trades" add constraint "trades_account_id_fkey" FOREIGN KEY (account_id) REFERENCES public.accounts(id) ON DELETE CASCADE not valid;

alter table "public"."trades" validate constraint "trades_account_id_fkey";

alter table "public"."trades" add constraint "trades_source_check" CHECK ((source = ANY (ARRAY['mt4'::text, 'mt5'::text, 'csv'::text, 'manual'::text, 'excel'::text, 'telegram'::text]))) not valid;

alter table "public"."trades" validate constraint "trades_source_check";

set check_function_bodies = off;

CREATE OR REPLACE FUNCTION public.rls_auto_enable()
 RETURNS event_trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog'
AS $function$
DECLARE
  cmd record;
BEGIN
  FOR cmd IN
    SELECT *
    FROM pg_event_trigger_ddl_commands()
    WHERE command_tag IN ('CREATE TABLE', 'CREATE TABLE AS', 'SELECT INTO')
      AND object_type IN ('table','partitioned table')
  LOOP
     IF cmd.schema_name IS NOT NULL AND cmd.schema_name IN ('public') AND cmd.schema_name NOT IN ('pg_catalog','information_schema') AND cmd.schema_name NOT LIKE 'pg_toast%' AND cmd.schema_name NOT LIKE 'pg_temp%' THEN
      BEGIN
        EXECUTE format('alter table if exists %s enable row level security', cmd.object_identity);
        RAISE LOG 'rls_auto_enable: enabled RLS on %', cmd.object_identity;
      EXCEPTION
        WHEN OTHERS THEN
          RAISE LOG 'rls_auto_enable: failed to enable RLS on %', cmd.object_identity;
      END;
     ELSE
        RAISE LOG 'rls_auto_enable: skip % (either system schema or not in enforced list: %.)', cmd.object_identity, cmd.schema_name;
     END IF;
  END LOOP;
END;
$function$
;

grant delete on table "public"."coaching_sessions" to "anon";

grant insert on table "public"."coaching_sessions" to "anon";

grant references on table "public"."coaching_sessions" to "anon";

grant select on table "public"."coaching_sessions" to "anon";

grant trigger on table "public"."coaching_sessions" to "anon";

grant truncate on table "public"."coaching_sessions" to "anon";

grant update on table "public"."coaching_sessions" to "anon";

grant delete on table "public"."coaching_sessions" to "authenticated";

grant insert on table "public"."coaching_sessions" to "authenticated";

grant references on table "public"."coaching_sessions" to "authenticated";

grant select on table "public"."coaching_sessions" to "authenticated";

grant trigger on table "public"."coaching_sessions" to "authenticated";

grant truncate on table "public"."coaching_sessions" to "authenticated";

grant update on table "public"."coaching_sessions" to "authenticated";

grant delete on table "public"."coaching_sessions" to "service_role";

grant insert on table "public"."coaching_sessions" to "service_role";

grant references on table "public"."coaching_sessions" to "service_role";

grant select on table "public"."coaching_sessions" to "service_role";

grant trigger on table "public"."coaching_sessions" to "service_role";

grant truncate on table "public"."coaching_sessions" to "service_role";

grant update on table "public"."coaching_sessions" to "service_role";

grant delete on table "public"."news" to "anon";

grant insert on table "public"."news" to "anon";

grant references on table "public"."news" to "anon";

grant select on table "public"."news" to "anon";

grant trigger on table "public"."news" to "anon";

grant truncate on table "public"."news" to "anon";

grant update on table "public"."news" to "anon";

grant delete on table "public"."news" to "authenticated";

grant insert on table "public"."news" to "authenticated";

grant references on table "public"."news" to "authenticated";

grant select on table "public"."news" to "authenticated";

grant trigger on table "public"."news" to "authenticated";

grant truncate on table "public"."news" to "authenticated";

grant update on table "public"."news" to "authenticated";

grant delete on table "public"."news" to "service_role";

grant insert on table "public"."news" to "service_role";

grant references on table "public"."news" to "service_role";

grant select on table "public"."news" to "service_role";

grant trigger on table "public"."news" to "service_role";

grant truncate on table "public"."news" to "service_role";

grant update on table "public"."news" to "service_role";


