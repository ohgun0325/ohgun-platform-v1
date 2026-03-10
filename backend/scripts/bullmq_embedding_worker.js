/**
 * BullMQ Worker: Upstash Redis 큐에서 임베딩 작업을 폴링하고 백엔드에 실행 요청.
 *
 * 설치:
 *   pnpm install bullmq ioredis dotenv
 *
 * 실행 (프로젝트 루트에서):
 *   node scripts/bullmq_embedding_worker.js
 *
 * 환경변수: 프로젝트 루트 .env 에서 자동 로드
 *   UPSTASH_REDIS_REST_URL, UPSTASH_REDIS_REST_TOKEN, BACKEND_API_URL (선택)
 */

require('dotenv').config(); // 프로젝트 루트 .env 로드

const { Queue, Worker } = require('bullmq');
const Redis = require('ioredis');

// Upstash Redis 연결 (ioredis 형식)
const REDIS_URL = process.env.UPSTASH_REDIS_REST_URL || '';
const REDIS_TOKEN = process.env.UPSTASH_REDIS_REST_TOKEN || '';
const BACKEND_API_URL = process.env.BACKEND_API_URL || 'http://localhost:8000';

if (!REDIS_URL || !REDIS_TOKEN) {
  console.error('❌ UPSTASH_REDIS_REST_URL 또는 UPSTASH_REDIS_REST_TOKEN 이 설정되지 않았습니다.');
  process.exit(1);
}

// Upstash REST → ioredis 연결 (URL 파싱)
// Upstash REST URL 예: https://powerful-kit-16749.upstash.io
// ioredis는 host:port 형태이므로 변환 필요
const redisHost = REDIS_URL.replace('https://', '').replace('http://', '');
const redisConnection = new Redis({
  host: redisHost,
  port: 6379, // Upstash는 기본 6379 또는 6380(TLS)
  password: REDIS_TOKEN,
  tls: {}, // HTTPS → TLS 필요
  maxRetriesPerRequest: null, // BullMQ 권장
  enableReadyCheck: false,
});

// BullMQ Queue 생성 (Python에서 rpush한 키와 동일)
const QUEUE_NAME = 'embedding-jobs'; // bull:embedding-jobs 에서 bull: 프리픽스는 BullMQ가 자동 추가
const queue = new Queue(QUEUE_NAME, { connection: redisConnection });

console.log('🚀 BullMQ Embedding Worker 시작');
console.log(`   - Queue: ${QUEUE_NAME}`);
console.log(`   - Backend: ${BACKEND_API_URL}`);

// Worker: 큐에서 job을 꺼내 백엔드 API 호출
const worker = new Worker(
  QUEUE_NAME,
  async (job) => {
    const { job_id, domain, entity_type, limit, add } = job.data;
    console.log(`\n📦 [${job_id}] 임베딩 작업 시작: ${domain}/${entity_type}${add ? ' (추가 모드)' : ''}`);

    try {
      // 백엔드 임베딩 실행 엔드포인트 호출
      const params = new URLSearchParams({ job_id });
      if (limit != null) params.set('limit', String(limit));
      if (add === true) params.set('add', 'true');
      const url = `${BACKEND_API_URL}/api/v10/class/soccer/player/embedding/execute?${params.toString()}`;
      const response = await fetch(url, { method: 'POST' });
      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.detail || `HTTP ${response.status}`);
      }

      console.log(`✅ [${job_id}] 임베딩 완료:`, result.result?.message || result.status);
      return result;
    } catch (error) {
      console.error(`❌ [${job_id}] 임베딩 실패:`, error.message);
      throw error;
    }
  },
  {
    connection: redisConnection,
    concurrency: 1, // 동시 처리 작업 수 (1이면 순차 처리)
  }
);

// Worker 이벤트 핸들러
worker.on('completed', (job) => {
  console.log(`✅ Job ${job.id} completed`);
});

worker.on('failed', (job, err) => {
  console.error(`❌ Job ${job?.id} failed:`, err.message);
});

worker.on('error', (err) => {
  console.error('⚠️  Worker error:', err);
});

// Redis 토큰 유효성 주기적 체크 (5분마다)
setInterval(async () => {
  try {
    await redisConnection.ping();
    console.log('🔄 Redis 연결 유효');
  } catch (error) {
    console.error('❌ Redis 토큰 만료 또는 연결 실패. Worker 종료.');
    await worker.close();
    process.exit(1);
  }
}, 5 * 60 * 1000);

console.log('⏳ 임베딩 작업 대기 중...\n');
