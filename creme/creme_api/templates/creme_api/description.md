# Drive Creme CRM from the outside

Welcome on the technical documentation of the Creme CRM API.

This page introduces the technical characteristics of the API.

All urls in this document are relative to the api base url: [{{ creme_root_url }}]({{ creme_root_url }})

## Authentication

In order to authenticate, you must first define an application.
An application represents an external tool or process which needs to access Creme through its API.
It's identified by its name, and defines various configuration variables related to the service 
integration, and security options.

At creation time, an application is assigned an **Application ID** and an **Application Secret**.
This id and password pair will allow you to create access tokens.
The application secret will be displayed only once.

To create a token using the application ID and application secret, use the [Tokens endpoint](#/Tokens).

```
{
  "token": "long-token-string",
  "token_type": "token",
  "expires_in": 3600
}
```
Here we can see this token is valid for the next `3600` seconds.

It must then be provided in each API call in the `Authorization` HTTP header.

```
Authorization: {token_type} {token}

Authorization: token long-token-string
```

## Pagination

When listing resources you can control the number of results return per page using the `page_size` query parameter.
```
GET {{ creme_root_url }}creme_api/{resource}/?page_size=10
```

results will be returned in that form:
```
{
  "next": "{{ creme_root_url }}creme_api/{resource}/?cursor=cD05Mw%3D%3D&page_size=10",
  "previous": null,
  "results": [
    ...
  ]
}
```
To fetch the next page, use the "next" url, which defines a `cursor` query parameter:
```
GET {{ creme_root_url }}creme_api/{resource}/?cursor=cD05Mw%3D%3D&page_size=10
```
