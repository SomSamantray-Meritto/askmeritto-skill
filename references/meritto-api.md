# Meritto / NoPaperForms Developer API (cached snapshot)

**Primary path is the Postman MCP, not this file.** `developer.nopaperforms.com` is a Postman-Documenter
SPA that WebFetch cannot read, so the skill calls the Postman MCP:

- Tool: `getCollection`
- `collectionId`: `10228290-dbfa007b-61e7-4f65-bc5d-df17c46257e9`
- For full per-endpoint detail (params, example curl, response, examples) add `model=full` or fetch the
  specific request item.
- Base URL variable: `https://api.nopaperforms.io`
- Live portal (always link in answers): `https://developer.nopaperforms.com/`

This file is the **fallback** for hosts where the Postman MCP is not connected. It records the endpoint
map captured from the collection (verified). Per-endpoint argument/curl detail comes from the live MCP;
when answering from this snapshot, say so and link the portal.

## Endpoint map

**Overview** (cross-cutting): Auth · HTTP Response Codes · Error Handling · Pagination

**Lead:** Create Lead · Update Lead · Create or Update Lead · Get Lead Fields · Get Lead Details by ID ·
Get Lead Details by Email · Get Lead Details by Mobile Number · Bulk Lead Delete · Get Status of Bulk Lead
Delete · Bulk Lead Create or Update · Get Lead List

**Opportunity:** Create Opportunity · Update Opportunity

**Activity:** Get Activity Codes · Get Activity by Lead ID · Get Activity by Date Range

**Form:** Get Forms list · Get Field Details

**Master Data:** Get Master Data List · Get Master Data Child by ID · Create Master Data · Update Master
Data · Add Values in Master Data · Update Value in Master Data · Get Master Data Details by ID

**Payment:** Get Payment Product List · Get Payment Details

**User, Role & Permission:** Create a User · Update a User · Get User details by ID · Get Roles list ·
Get Permission Group list · Get Users list

**Team & Hierarchy:** Get Teams list

**Query (tickets):** Get Ticket Category · Get Ticket list · Get Ticket Details by Ticket_id

**Application:** Create Application · Update Application · Create or Update Application · Get Application
Details · Get Application Stage · Get Application Sub Stage · Get Paragraph Details

## Answer contract for DEVELOPER_API

Always give: endpoint name, method + URL (base `api.nopaperforms.io`), mandatory params, optional params,
example curl, example response, error handling / status codes (from Overview), auth note (from Overview →
Auth), and the portal link.
