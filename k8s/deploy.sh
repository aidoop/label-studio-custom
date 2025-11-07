#!/bin/bash
# ==============================================================================
# Label Studio Kubernetes 배포 스크립트
# ==============================================================================

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 로그 함수
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 배너
echo "================================================================"
echo "  Label Studio Kubernetes 배포"
echo "  Version: 1.20.0-sso.25"
echo "================================================================"
echo ""

# kubectl 확인
if ! command -v kubectl &> /dev/null; then
    log_error "kubectl이 설치되어 있지 않습니다."
    exit 1
fi

log_info "kubectl 버전: $(kubectl version --client --short)"

# 클러스터 연결 확인
if ! kubectl cluster-info &> /dev/null; then
    log_error "Kubernetes 클러스터에 연결할 수 없습니다."
    log_error "aws eks update-kubeconfig --region ap-northeast-2 --name YOUR-CLUSTER-NAME"
    exit 1
fi

log_info "클러스터 연결 확인 완료"

# 배포 옵션
NAMESPACE="label-studio"
DRY_RUN=${DRY_RUN:-false}

if [ "$DRY_RUN" = "true" ]; then
    log_warn "DRY RUN 모드: 실제로 적용되지 않습니다."
    KUBECTL_OPTS="--dry-run=client"
else
    KUBECTL_OPTS=""
fi

# 1. Namespace 생성
log_info "1/8 Namespace 생성..."
kubectl apply -f 00-namespace.yaml $KUBECTL_OPTS
sleep 1

# 2. Secret 생성
log_info "2/8 Secret 생성..."
if kubectl get secret label-studio-secret -n $NAMESPACE &> /dev/null; then
    log_warn "Secret이 이미 존재합니다. 스킵..."
else
    kubectl apply -f 01-secret.yaml $KUBECTL_OPTS
fi
sleep 1

# 3. ConfigMap 생성
log_info "3/8 ConfigMap 생성..."
kubectl apply -f 02-configmap.yaml $KUBECTL_OPTS
sleep 1

# 4. PVC 생성
log_info "4/8 PersistentVolumeClaim 생성..."
if kubectl get pvc label-studio-data -n $NAMESPACE &> /dev/null; then
    log_warn "PVC가 이미 존재합니다. 스킵..."
else
    kubectl apply -f 03-pvc.yaml $KUBECTL_OPTS
fi
sleep 1

# 5. Deployment 생성
log_info "5/8 Deployment 생성..."
kubectl apply -f 04-deployment.yaml $KUBECTL_OPTS
sleep 2

# 6. Service 생성
log_info "6/8 Service 생성..."
kubectl apply -f 05-service.yaml $KUBECTL_OPTS
sleep 1

# 7. Ingress 생성
log_info "7/8 Ingress 생성..."
if [ -f "06-ingress-alb.yaml" ]; then
    log_info "ALB Ingress를 생성합니다..."
    kubectl apply -f 06-ingress-alb.yaml $KUBECTL_OPTS
elif [ -f "06-ingress-nginx.yaml" ]; then
    log_info "NGINX Ingress를 생성합니다..."
    kubectl apply -f 06-ingress-nginx.yaml $KUBECTL_OPTS
else
    log_warn "Ingress 파일을 찾을 수 없습니다."
fi
sleep 1

# 8. HPA 생성 (선택사항)
log_info "8/8 HorizontalPodAutoscaler 생성..."
if [ -f "07-hpa.yaml" ]; then
    kubectl apply -f 07-hpa.yaml $KUBECTL_OPTS
else
    log_warn "HPA 파일을 찾을 수 없습니다. 스킵..."
fi

echo ""
log_info "배포 완료!"
echo ""

# 배포 상태 확인
if [ "$DRY_RUN" != "true" ]; then
    echo "================================================================"
    echo "  배포 상태 확인"
    echo "================================================================"
    echo ""

    log_info "Pod 상태:"
    kubectl get pods -n $NAMESPACE

    echo ""
    log_info "Service 상태:"
    kubectl get service -n $NAMESPACE

    echo ""
    log_info "Ingress 상태:"
    kubectl get ingress -n $NAMESPACE

    echo ""
    log_info "배포 완료 대기 중..."
    kubectl rollout status deployment/label-studio -n $NAMESPACE --timeout=5m

    echo ""
    echo "================================================================"
    echo "  다음 단계"
    echo "================================================================"
    echo ""
    echo "1. ALB 엔드포인트 확인:"
    echo "   kubectl get ingress label-studio -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'"
    echo ""
    echo "2. DNS 레코드 생성 (Route 53):"
    echo "   - A 레코드 (Alias) 생성"
    echo "   - ALB를 대상으로 설정"
    echo ""
    echo "3. 초기 사용자 생성:"
    echo "   POD_NAME=\$(kubectl get pods -n $NAMESPACE -l app=label-studio -o jsonpath='{.items[0].metadata.name}')"
    echo "   kubectl exec -it \$POD_NAME -n $NAMESPACE -- label-studio user --username admin@hatiolab.com --password admin123"
    echo ""
    echo "4. 접속:"
    echo "   https://label.hatiolab.com"
    echo ""
fi
