# ECS Cluster and Service Configuration

resource "aws_cloudwatch_log_group" "api" {
  name              = "/ecs/recycling-buddy-api"
  retention_in_days = 14

  tags = {
    Project = "recycling-buddy"
  }
}

resource "aws_ecs_cluster" "main" {
  name = "recycling-buddy"

  setting {
    name  = "containerInsights"
    value = "disabled"
  }

  tags = {
    Project = "recycling-buddy"
  }
}

resource "aws_ecs_task_definition" "api" {
  family                   = "recycling-buddy-api"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.api_cpu
  memory                   = var.api_memory
  execution_role_arn       = var.ecs_execution_role_arn
  task_role_arn            = var.ecs_task_role_arn

  container_definitions = jsonencode([
    {
      name  = "api"
      image = "${aws_ecr_repository.api.repository_url}:latest"

      portMappings = [
        {
          containerPort = 8000
          protocol      = "tcp"
        }
      ]

      environment = [
        {
          name  = "S3_BUCKET"
          value = aws_s3_bucket.data.id
        },
        {
          name  = "AWS_REGION"
          value = var.aws_region
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.api.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "api"
        }
      }

      essential = true
    }
  ])

  tags = {
    Project = "recycling-buddy"
  }
}

resource "aws_security_group" "ecs_tasks" {
  name        = "recycling-buddy-ecs-tasks-sg"
  description = "Security group for ECS tasks"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
    description     = "Allow traffic from ALB"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }

  tags = {
    Name    = "recycling-buddy-ecs-tasks-sg"
    Project = "recycling-buddy"
  }
}

resource "aws_ecs_service" "api" {
  name            = "recycling-buddy-api"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = var.api_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.public[*].id
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "api"
    container_port   = 8000
  }

  # Allow CI/CD to manage task definition updates
  lifecycle {
    ignore_changes = [task_definition]
  }

  tags = {
    Project = "recycling-buddy"
  }
}
