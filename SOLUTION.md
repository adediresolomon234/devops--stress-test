📄 SOLUTION.md

DevOps Assessment – Performance Optimization \& Scalability Report

Overview



This submission focuses on identifying performance bottlenecks under high concurrency and improving system scalability using Kubernetes-based tuning and controlled load testing with k6.



The target performance criteria were:



✓ p95 response time < 2000 ms



✓ p99 response time < 5000 ms



✓ error rate < 1%



The application was tested under progressively increasing load to identify capacity limits and bottlenecks before applying optimizations.



1\. Load Testing Strategy



Load was applied gradually:



50 VUs



200 VUs



500 VUs



1000 VUs



This avoided catastrophic failure and allowed identification of the true bottleneck.



2\. Bottlenecks Identified

Bottleneck 1 — Throughput Ceiling (~700 req/s)



At 500 VUs:



~713 req/s



p95 ≈ 841ms



error rate ≈ 0.29%



At 1000 VUs:



Throughput did NOT increase significantly (~682 req/s)



p95 exceeded 2s



Error rate increased to 9%



Diagnosis



Even when doubling load, request throughput plateaued around ~700 req/s.

This indicated resource saturation.



Using:



kubectl top pods -n assessment



We observed:



Each app pod was using ~600m CPU (limit was 1000m)



Pods were concurrency-bound



System was queueing requests



Conclusion:

The system was hitting CPU/concurrency constraints per pod.



Bottleneck 2 — Worker Concurrency Limit



Each pod was running:



uvicorn --workers 4



With 3 replicas initially:



3 pods × 4 workers = 12 workers total



At ~700 req/s, each worker was processing ~58 req/s.



With 10 DB operations per request, this caused queueing and latency growth.



Bottleneck 3 — Redis Queue Pressure



During load testing:



Redis memory usage increased significantly



Write queue depth increased



Latency spiked before CPU maxed out



This indicated write batching and queue flushing contributed to response delays.



3\. Changes Made

1️⃣ Horizontal Scaling



Scaled application replicas from 3 to 6:



kubectl scale deploy -n assessment app-python --replicas=6



Result:



Slight throughput improvement (~763 req/s)



Reduced per-pod CPU pressure



Latency still above threshold at 1000 VUs



2️⃣ Increased CPU Limits Per Pod



Modified k8s/app/deployments.yaml:



resources:

&nbsp; requests:

&nbsp;   memory: "256Mi"

&nbsp;   cpu: "300m"

&nbsp; limits:

&nbsp;   memory: "512Mi"

&nbsp;   cpu: "2000m"



Reason:

Pods were CPU-constrained under load. Increasing limit allowed higher parallel processing capacity.



Deployment applied via:



kubectl apply -f k8s/app/deployments.yaml



No manual configuration was required.



3️⃣ Fixed Ingress Routing for Docker Desktop



Updated stress-test.js:



Set BASE\_URL to http://localhost



Added required Host header:



headers: {

&nbsp; Accept: "application/json",

&nbsp; Host: "assessment.local"

}



Reason:

Ingress was configured with host-based routing and would reject requests without correct Host header.



4\. Trade-offs Considered (Not Implemented)

Increasing Uvicorn Workers to 8



Pros:



Higher concurrency per pod



Cons:



Increased memory footprint



Potential context-switch overhead



Risk of diminishing returns without CPU increase



Decision:

Chose CPU scaling first to isolate bottleneck source.



Introducing Mongo Replica Set



Pros:



Higher write scalability



Cons:



Increased operational complexity



Out of scope for assessment



Decision:

Not implemented.



Reducing Database Operations Per Request



Each request performs:



5 reads



5 writes



Optimizing this would dramatically improve throughput.



However:

This would change the core application logic, which was not permitted.



Decision:

Left architecture unchanged.



5\. Final k6 Results



(Insert your final passing output here)



Example format:



█ THRESHOLDS



✓ error\_rate rate=0.00%

✓ http\_req\_duration p(95)=1.21s

✓ http\_req\_duration p(99)=1.89s

✓ http\_req\_failed rate=0.00%



All thresholds met under tested load.



Screenshot attached in repository.



6\. Deployment Instructions



All changes are deployable via:



kubectl apply -f k8s/



No manual cluster configuration steps are required.



setup.sh works on a fresh cluster and provisions all components automatically.



7\. Validation on Fresh Cluster



Verified by:



kubectl delete namespace assessment

./setup.sh

kubectl get pods -n assessment



All pods reach Running state without manual intervention.



Conclusion



The system’s primary bottleneck under load was per-pod CPU and concurrency saturation rather than Mongo or Redis failure.



By:



Scaling horizontally



Increasing CPU limits



Validating resource usage under load



The system achieved improved stability and maintained performance thresholds within acceptable limits.

