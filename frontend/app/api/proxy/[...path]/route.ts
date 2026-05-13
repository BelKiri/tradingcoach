import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL =
  process.env.BACKEND_URL || "http://localhost:8000";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const { path } = await params;
  const target = `${BACKEND_URL}/${path.join("/")}${request.nextUrl.search}`;

  const res = await fetch(target, {
    headers: forwardHeaders(request),
  });

  return proxyResponse(res);
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const { path } = await params;
  const target = `${BACKEND_URL}/${path.join("/")}${request.nextUrl.search}`;

  const contentType = request.headers.get("content-type") || "";
  const body = contentType.includes("json")
    ? JSON.stringify(await request.json())
    : await request.arrayBuffer();

  const res = await fetch(target, {
    method: "POST",
    headers: forwardHeaders(request),
    body,
  });

  return proxyResponse(res);
}

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const { path } = await params;
  const target = `${BACKEND_URL}/${path.join("/")}${request.nextUrl.search}`;

  const contentType = request.headers.get("content-type") || "";
  const body = contentType.includes("json")
    ? JSON.stringify(await request.json())
    : await request.arrayBuffer();

  const res = await fetch(target, {
    method: "PATCH",
    headers: forwardHeaders(request),
    body,
  });

  return proxyResponse(res);
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const { path } = await params;
  const target = `${BACKEND_URL}/${path.join("/")}${request.nextUrl.search}`;

  const res = await fetch(target, {
    method: "DELETE",
    headers: forwardHeaders(request),
  });

  return proxyResponse(res);
}

function forwardHeaders(request: NextRequest): HeadersInit {
  const headers: Record<string, string> = {};
  const contentType = request.headers.get("content-type");
  if (contentType) headers["content-type"] = contentType;
  const auth = request.headers.get("authorization");
  if (auth) headers["authorization"] = auth;
  return headers;
}

async function proxyResponse(res: Response): Promise<NextResponse> {
  const data = await res.arrayBuffer();
  return new NextResponse(data, {
    status: res.status,
    headers: {
      "content-type": res.headers.get("content-type") || "application/json",
    },
  });
}
