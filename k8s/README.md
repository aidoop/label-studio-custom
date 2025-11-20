# Label Studio Kubernetes 배포 가이드 (AWS EKS)

이 가이드는 AWS EKS 환경에 Label Studio Custom을 배포하는 방법을 설명합니다.

## 📋 목차

- [사전 요구사항](#사전-요구사항)
- [배포 아키텍처](#배포-아키텍처)
- [배포 순서](#배포-순서)
- [환경 설정](#환경-설정)
- [배포 실행](#배포-실행)
- [배포 후 작업](#배포-후-작업)
- [문제 해결](#문제-해결)
- [유지보수](#유지보수)

---

## 사전 요구사항

### 1. AWS 리소스

- **EKS 클러스터**: Kubernetes 1.24 이상
- **Aurora PostgreSQL**: v13 이상
  - 엔드포인트: `your-aurora-endpoint.rds.amazonaws.com`
  - 데이터베이스: `labelstudio`
  - 사용자: `postgres`
  - 비밀번호: 안전하게 보관
- **ACM 인증서**: `label.hatiolab.com`용 HTTPS 인증서
- **EBS CSI Driver**: 데이터 영속성 스토리지용
- **AWS Load Balancer Controller**: ALB 프로비저닝용

### 2. 로컬 도구

```bash
# kubectl 설치 (v1.24 이상)
kubectl version --client

# AWS CLI 설치
aws --version

# EKS 클러스터 접근 설정
aws eks update-kubeconfig --region ap-northeast-2 --name YOUR-CLUSTER-NAME

# 연결 확인
kubectl cluster-info
```

### 3. 필수 Add-on 설치

#### EBS CSI Driver

```bash
# EBS CSI Driver 설치
kubectl apply -k "github.com/kubernetes-sigs/aws-ebs-csi-driver/deploy/kubernetes/overlays/stable/?ref=release-1.25"

# 확인
kubectl get pods -n kube-system | grep ebs-csi
```

#### AWS Load Balancer Controller

```bash
# Helm 설치 (없는 경우)
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# AWS Load Balancer Controller 설치
helm repo add eks https://aws.github.io/eks-charts
helm repo update

helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=YOUR-CLUSTER-NAME \
  --set serviceAccount.create=false \
  --set serviceAccount.name=aws-load-balancer-controller

# 확인
kubectl get deployment -n kube-system aws-load-balancer-controller
```

#### Metrics Server (HPA 사용 시)

```bash
# Metrics Server 설치
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# 확인
kubectl top nodes
```

---

## 배포 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                         AWS Cloud                                │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                      EKS Cluster                           │  │
│  │                                                             │  │
│  │  ┌─────────────┐      ┌──────────────────────────────┐   │  │
│  │  │   Ingress   │      │      Namespace: label-studio  │   │  │
│  │  │    (ALB)    │─────▶│                               │   │  │
│  │  │             │      │  ┌────────────────────────┐   │   │  │
│  │  │ HTTPS: 443  │      │  │   Deployment (2+ Pods) │   │   │  │
│  │  │ HTTP: 80    │      │  │  - Label Studio App    │   │   │  │
│  │  └─────────────┘      │  │  - SSO Integrated      │   │   │  │
│  │                        │  └──────────┬─────────────┘   │   │  │
│  │                        │             │                  │   │  │
│  │  ┌─────────────┐      │  ┌──────────▼─────────────┐   │   │  │
│  │  │     EBS     │◀─────┼──│  PersistentVolume      │   │   │  │
│  │  │   (gp3)     │      │  │  - 20Gi Storage        │   │   │  │
│  │  └─────────────┘      │  └────────────────────────┘   │   │  │
│  │                        │                               │   │  │
│  │                        │  ┌────────────────────────┐   │   │  │
│  │                        │  │  ConfigMap + Secret    │   │   │  │
│  │                        │  │  - Environment Vars    │   │   │  │
│  │                        │  └────────────────────────┘   │   │  │
│  │                        └───────────────────────────────┘   │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │                   Aurora PostgreSQL                      │  │
│  │  - Endpoint: your-aurora-endpoint.rds.amazonaws.com     │  │
│  │  - Database: labelstudio                                 │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │                  Certificate Manager                     │  │
│  │  - Domain: label.hatiolab.com                           │  │
│  │  - SSL/TLS Certificate                                   │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 배포 순서

### 1단계: 환경 설정

#### 1.1 Aurora PostgreSQL 준비

```sql
-- Aurora PostgreSQL에 연결
psql -h your-aurora-endpoint.rds.amazonaws.com -U postgres

-- 데이터베이스 생성
CREATE DATABASE labelstudio;

-- 사용자 생성 (선택사항)
CREATE USER labelstudio_user WITH PASSWORD 'your-strong-password';
GRANT ALL PRIVILEGES ON DATABASE labelstudio TO labelstudio_user;

-- 확인
\l
\q
```

#### 1.2 ACM 인증서 생성

```bash
# AWS Console에서:
# 1. Certificate Manager 서비스 접속
# 2. "Request a certificate" 클릭
# 3. Domain name: label.hatiolab.com
# 4. DNS 검증 선택
# 5. Route 53에서 검증 레코드 추가
# 6. 인증서 ARN 복사

# 또는 AWS CLI로:
aws acm request-certificate \
  --domain-name label.hatiolab.com \
  --validation-method DNS \
  --region ap-northeast-2

# 인증서 ARN 확인
aws acm list-certificates --region ap-northeast-2
```

#### 1.3 매니페스트 파일 수정

**k8s/01-secret.yaml**:

```bash
# PostgreSQL 비밀번호 인코딩
echo -n "your-aurora-password" | base64

# Django Secret Key 생성 및 인코딩
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())" | base64

# 01-secret.yaml 파일의 data 섹션 수정
```

**k8s/02-configmap.yaml**:

```yaml
# 다음 값들을 수정:
POSTGRES_HOST: "your-aurora-endpoint.rds.amazonaws.com"
POSTGRES_DB: "labelstudio"
POSTGRES_USER: "postgres"
LABEL_STUDIO_HOST: "https://label.hatiolab.com"
```

**k8s/06-ingress-alb.yaml**:

```yaml
# ACM 인증서 ARN 수정:
alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:ap-northeast-2:ACCOUNT-ID:certificate/CERTIFICATE-ID

# 호스트명 확인:
spec:
  rules:
    - host: label.hatiolab.com
```

---

## 배포 실행

### 전체 배포 (권장)

```bash
# 1. Namespace 생성
kubectl apply -f k8s/00-namespace.yaml

# 2. Secret 생성
kubectl apply -f k8s/01-secret.yaml

# 3. ConfigMap 생성
kubectl apply -f k8s/02-configmap.yaml

# 4. PVC 생성
kubectl apply -f k8s/03-pvc.yaml

# 5. Deployment 생성
kubectl apply -f k8s/04-deployment.yaml

# 6. Service 생성
kubectl apply -f k8s/05-service.yaml

# 7. Ingress 생성 (ALB)
kubectl apply -f k8s/06-ingress-alb.yaml

# 8. HPA 생성 (선택사항)
kubectl apply -f k8s/07-hpa.yaml
```

### 원스텝 배포

```bash
# 모든 매니페스트를 한 번에 적용
kubectl apply -f k8s/
```

---

## 배포 후 작업

### 1. 배포 상태 확인

```bash
# Pod 상태 확인
kubectl get pods -n label-studio

# 예상 출력:
# NAME                             READY   STATUS    RESTARTS   AGE
# label-studio-xxxxxxxxxx-xxxxx    1/1     Running   0          2m
# label-studio-xxxxxxxxxx-xxxxx    1/1     Running   0          2m

# Deployment 상태 확인
kubectl get deployment -n label-studio

# Service 상태 확인
kubectl get service -n label-studio

# Ingress 상태 확인
kubectl get ingress -n label-studio

# ALB 생성 확인 (2-3분 소요)
kubectl describe ingress label-studio -n label-studio
```

### 2. ALB 엔드포인트 확인

```bash
# ALB DNS 이름 확인
kubectl get ingress label-studio -n label-studio -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'

# 예상 출력:
# k8s-labelstu-labelstu-xxxxxxxxxx-xxxxxxxxxx.ap-northeast-2.elb.amazonaws.com
```

### 3. DNS 레코드 생성

```bash
# Route 53에서:
# 1. 호스팅 영역 (hatiolab.com) 선택
# 2. "Create record" 클릭
# 3. Record name: label
# 4. Record type: A (Alias)
# 5. Route traffic to: Alias to Application Load Balancer
# 6. Region: ap-northeast-2
# 7. ALB 선택
# 8. "Create records" 클릭
```

### 4. 초기 사용자 생성

```bash
# Pod 이름 확인
POD_NAME=$(kubectl get pods -n label-studio -l app=label-studio -o jsonpath='{.items[0].metadata.name}')

# Admin 사용자 생성
kubectl exec -it $POD_NAME -n label-studio -- \
  label-studio user \
  --username admin@hatiolab.com \
  --password admin123

# API 토큰 생성
kubectl exec -it $POD_NAME -n label-studio -- \
  label-studio user \
  --username admin@hatiolab.com \
  --user-token
```

### 5. 접속 확인

```bash
# 웹 브라우저에서:
https://label.hatiolab.com

# 헬스체크 확인
curl -k https://label.hatiolab.com/health

# 예상 응답:
# {"status":"UP"}
```

---

## 문제 해결

### Pod가 시작되지 않는 경우

```bash
# Pod 로그 확인
kubectl logs -n label-studio POD_NAME

# Pod 상세 정보 확인
kubectl describe pod -n label-studio POD_NAME

# 일반적인 문제:
# 1. Aurora PostgreSQL 연결 실패
#    - 보안 그룹 확인: EKS 노드에서 Aurora로 5432 포트 허용
#    - 엔드포인트 확인: ConfigMap의 POSTGRES_HOST
# 2. 이미지 Pull 실패
#    - 이미지 이름 확인: ghcr.io/aidoop/label-studio-custom:1.20.0-sso.38
# 3. Secret/ConfigMap 오류
#    - base64 인코딩 확인
```

### ALB가 생성되지 않는 경우

```bash
# AWS Load Balancer Controller 로그 확인
kubectl logs -n kube-system deployment/aws-load-balancer-controller

# Ingress 이벤트 확인
kubectl describe ingress label-studio -n label-studio

# 일반적인 문제:
# 1. AWS Load Balancer Controller 미설치
# 2. IAM 권한 부족
# 3. 서브넷 태그 누락 (퍼블릭 서브넷에 kubernetes.io/role/elb=1)
```

### 데이터베이스 마이그레이션 실패

```bash
# Init Container 로그 확인
kubectl logs -n label-studio POD_NAME -c migrate

# 수동 마이그레이션 실행
kubectl exec -it $POD_NAME -n label-studio -- label-studio migrate
```

### HTTPS 인증서 오류

```bash
# ACM 인증서 상태 확인
aws acm describe-certificate \
  --certificate-arn YOUR-CERTIFICATE-ARN \
  --region ap-northeast-2

# Ingress annotation 확인
kubectl get ingress label-studio -n label-studio -o yaml | grep certificate-arn
```

---

## 유지보수

### 로그 확인

```bash
# 실시간 로그
kubectl logs -f -n label-studio deployment/label-studio

# 특정 Pod 로그
kubectl logs -n label-studio POD_NAME

# 이전 Pod 로그 (재시작된 경우)
kubectl logs -n label-studio POD_NAME --previous
```

### 스케일링

```bash
# 수동 스케일링
kubectl scale deployment label-studio -n label-studio --replicas=5

# HPA 상태 확인
kubectl get hpa -n label-studio

# 현재 리소스 사용량 확인
kubectl top pods -n label-studio
```

### 업데이트

```bash
# 이미지 업데이트
kubectl set image deployment/label-studio \
  label-studio=ghcr.io/aidoop/label-studio-custom:NEW-VERSION \
  -n label-studio

# 롤링 업데이트 상태 확인
kubectl rollout status deployment/label-studio -n label-studio

# 롤백
kubectl rollout undo deployment/label-studio -n label-studio
```

### 데이터 백업

```bash
# PostgreSQL 백업 (Aurora 스냅샷 권장)
aws rds create-db-cluster-snapshot \
  --db-cluster-snapshot-identifier labelstudio-backup-$(date +%Y%m%d) \
  --db-cluster-identifier YOUR-AURORA-CLUSTER-ID

# PVC 데이터 백업 (Velero 권장)
# https://velero.io/docs/
```

### 리소스 정리

```bash
# 전체 삭제
kubectl delete -f k8s/

# 또는 개별 삭제
kubectl delete namespace label-studio

# PVC는 별도로 삭제해야 함
kubectl delete pvc label-studio-data -n label-studio
```

---

## 참고 자료

- [Label Studio Custom 저장소](https://github.com/aidoop/label-studio-custom)
- [AWS EKS 문서](https://docs.aws.amazon.com/eks/)
- [AWS Load Balancer Controller](https://kubernetes-sigs.github.io/aws-load-balancer-controller/)
- [EBS CSI Driver](https://github.com/kubernetes-sigs/aws-ebs-csi-driver)
- [Kubernetes 문서](https://kubernetes.io/docs/)

---

## 지원

문제가 발생하면 다음을 확인하세요:

1. GitHub Issues: [label-studio-custom Issues](https://github.com/aidoop/label-studio-custom/issues)
2. Kubernetes 이벤트: `kubectl get events -n label-studio --sort-by='.lastTimestamp'`
3. Pod 로그: `kubectl logs -n label-studio POD_NAME`
4. AWS 리소스 상태 확인
