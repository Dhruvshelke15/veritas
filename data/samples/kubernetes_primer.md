# Kubernetes Primer

## What is Kubernetes

Kubernetes is an open source container orchestration platform that automates the deployment, scaling, and management of containerized applications. It was originally designed by Google and is now maintained by the Cloud Native Computing Foundation.

## Pods

A Pod is the smallest deployable unit in Kubernetes. A Pod represents a single instance of a running process and can contain one or more containers that share storage and network resources. Containers in the same Pod always run on the same node and can communicate over localhost.

## Deployments

A Deployment provides declarative updates for Pods and ReplicaSets. You describe a desired state in a Deployment manifest, and the Deployment controller changes the actual state to the desired state at a controlled rate. Rolling updates replace Pods incrementally so the application stays available during upgrades.

## Services

A Service is an abstraction that defines a logical set of Pods and a policy to access them. Because Pods are ephemeral and their IP addresses change, Services provide a stable endpoint. The main Service types are ClusterIP, NodePort, and LoadBalancer.

## Horizontal Pod Autoscaling

The Horizontal Pod Autoscaler automatically scales the number of Pod replicas based on observed metrics such as CPU utilization or custom metrics. The autoscaler checks metrics at a regular interval, defaulting to fifteen seconds, and adjusts the replica count between configured minimum and maximum bounds.
