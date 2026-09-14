# Implementation research notes

The workflow intentionally uses n8n's Gmail **Reply** operation instead of creating a fresh email, preserving the existing conversation. n8n's current Gmail documentation describes Reply as replying to an existing message by Message ID and allows disabling the default n8n attribution and replying to sender only.

Reference: https://docs.n8n.io/integrations/builtin/app-nodes/n8n-nodes-base.gmail/message-operations/

The architecture also mirrors the brief's business priority: first response speed and conversion matter, but business facts must be grounded. AI therefore performs interpretation/rendering while deterministic logic owns state transitions and external action gates.
