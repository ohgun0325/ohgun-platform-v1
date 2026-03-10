import { NextRequest, NextResponse } from 'next/server';

/**
 * Refresh Token을 HttpOnly 쿠키에 저장하는 API 라우트
 * 
 * 보안 원칙:
 * - Refresh Token은 HttpOnly 쿠키에 저장 (XSS 공격 방지)
 * - Secure 플래그 사용 (HTTPS에서만 전송)
 * - SameSite=Strict 설정 (CSRF 공격 방지)
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { refreshToken } = body;

    if (!refreshToken) {
      return NextResponse.json(
        { error: 'Refresh token is required' },
        { status: 400 }
      );
    }

    // HttpOnly 쿠키 설정
    const response = NextResponse.json(
      { success: true, message: 'Refresh token stored in cookie' },
      { status: 200 }
    );

    // Refresh Token을 HttpOnly 쿠키에 저장
    response.cookies.set('refreshToken', refreshToken, {
      httpOnly: true,           // JavaScript로 접근 불가 (XSS 방지)
      secure: process.env.NODE_ENV === 'production', // HTTPS에서만 전송 (프로덕션)
      sameSite: 'strict',       // CSRF 공격 방지
      maxAge: 60 * 60 * 24 * 7, // 7일
      path: '/',                // 모든 경로에서 접근 가능
    });

    return response;
  } catch (error) {
    console.error('Error setting refresh token cookie:', error);
    return NextResponse.json(
      { error: 'Failed to set refresh token' },
      { status: 500 }
    );
  }
}

/**
 * Refresh Token 쿠키 삭제 (로그아웃)
 */
export async function DELETE(request: NextRequest) {
  const response = NextResponse.json(
    { success: true, message: 'Refresh token removed' },
    { status: 200 }
  );

  // 쿠키 삭제
  response.cookies.delete('refreshToken');

  return response;
}

