---
number: 6
title: Autenticação corporativa própria do Betsalel
date: 2026-11-12
status: Accepted
---

# ADR-0006: Autenticação corporativa própria do Betsalel

## Status

Accepted

## Context

O dashboard precisa de identidade para exibir o mapa e registrar alterações. Hoje existe apenas um bypass local opt-in para competências; o Portal autentica matrícula por LDAP e verifica usuário/perfil/permissão em PARAM_* Oracle.

## Decision

Substituir o bypass local por autenticação própria do Betsalel: bind matrícula/senha via LDAPS com validação de certificado; exigir usuário ativo, perfil ativo/não expirado e tela VOSKILL ativa no Oracle do Portal; usar PODE_VISUALIZAR para leitura e PODE_EDITAR para escrita; usar sessão HttpOnly, SameSite e TTL curto; negar por padrão.

## Consequences

Exige configurar LDAPS/certificado e credenciais read-only do Oracle Portal. O Portal não é chamado em runtime. Sessões precisam expirar; permissões serão carregadas no login e revalidadas segundo o TTL. O bypass local será removido ao concluir a troca. Testes usam LDAP/Oracle simulados; validação corporativa exige ambiente acessível.
