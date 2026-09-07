# Sanaacash Provider Contract

This document records the executable provider boundary used by Django. The customer application does not call these endpoints directly.

Source: the supplied `api 1 (59).pdf`. When legacy database values differ from this contract, the PDF is authoritative for provider execution.

## Connection

Base API URL is configured as the provider connection base, for example:

`https://sanaacash.yrbso.net/api/yr/`

Required credentials:

- `userid`
- `DomainName`
- `Username`
- `Password`

Token:

`md5(md5(Password) + transid + Username + mobile)`

`+` is string concatenation.

## Standard result handling

- `resultCode == 0`: accepted/success according to the operation.
- `resultCode == -2` or a description containing `under process`/`under proccess`: pending.
- `resultCode == 10xx`: provider error.
- Status is checked using `/info?action=status` when the operation is asynchronous.
- Status response uses `isDone` and `isBan` to distinguish completed, processing and banned/failed states.

## Yemen Mobile

- Query balance: `/yem?action=query` with `mobile`.
- Bill balance: `/yem?action=bill` with `mobile` and `amount`.
- Query offers: `/yem?action=queryoffer` with `mobile`.
- Bill offer: `/yem?action=billoffer` with `mobile`, `offerid`, `method` (`New`, `Renew`, `Remove`).
- Combined offer billing: `/offeryem?action=billoffer` with `mobile`, `offerkey`, `method`, `solfa` (`Y`/`N`).

Ordinary Yemen Mobile balance is an amount-based service and does not require a package branch.

## Yemen Post / ADSL / Line

- Bill: `/post?action=bill` with `mobile`, `amount`, `type` (`adsl` or `line`).
- Query: `/post?action=query` with `mobile`.

## Why

- Bill: `/why?action=bill` with `mobile`, `num`.
- Balance: same endpoint with `num` and `rasid`.
- Package: same endpoint with `num` and `packageid`.

## YOU

- Open balance billing: `/mtn?action=bill` with `mobile`, `num`, `type`, `israsid=1`.
- Immediate denomination recharge: `/mtn?action=bill` with `mobile`, `num`, `type`.
- Offers: `/mtnoffer` with `mobile`, `num`.

`type` is `prepaid` or `postpaid`.

## SabaPhone

- Recharge: `/sabaphone?action=bill` with `mobile`, `num`.
- Offers: `/sabaoffer` with `mobile`, `num`.
- South offers: `/sbayoffer` with `mobile`, `num`.
- South recharge: `/sbay?action=bill` with `mobile`, `num`.
- Units: `/sabaunits` with `mobile`, `num`.

## AdenNet

- Bill: `/adenet?action=bill` with `mobile`, `num`.
- Query: `/adenet?action=query` with `mobile`, `num`.

## Wholesale

- SabaPhone wholesale: `/sabagomla` with `mobile`, `num`.
- MTN/You wholesale: `/mtngomla` with `mobile`, `num`.
- Yemen Mobile wholesale: `/mobilegomla` with `mobile`, `num`.

## Yemen 4G

`/yem4g` supports `action=bill` with `type=1` package, `type=2` balance, `type=3` change package, and `action=query` for enquiry.

## Electricity / Water

`/electwater` uses `action=query` or `action=bill` and `act=elect` or `act=water`. Customer identity is represented by `customer_id` and `placeid` according to the supplied contract.

## Games and cards

`/gameswcards` uses the provider service type plus catalog code and customer identity fields. The service type is derived from the selected backend service code. Catalog `uniqcode` is selected server-side from the selected game product.

Known service types from the supplied contract include PUBG, Free Fire, Mobile Legends, Lords Mobile, Clash Royale, Genshin Impact, Clash of Clans, New State PUBG, Brawl Stars, Hay Day, Call of Duty, Boom Beach, Google Play, App Store, beIN Connect, Razer Gold, CrossFire, PlayStation, Visa, MasterCard, Likee and BIGO LIVE.

## Agent balance

`/info?action=balance` returns the provider account balance.

## Webhook

Django supplies a callback URL and request-specific secret. Sanaacash can report asynchronous completion/ban using the transaction id and message. The backend matches the callback to the transaction and never exposes provider credentials to the customer app.

## Operational rules

1. Generate a unique numeric `transid` for every provider operation.
2. Never accept provider-generated `num`, `packageid`, `external_code` or game `uniqcode` from the customer as authoritative values.
3. Resolve provider values from the selected server-side catalog item.
4. Keep idempotency at the customer API boundary so a retry cannot reserve/submit the same paid request twice.
5. Keep pending operations pending until webhook/status confirms them.
