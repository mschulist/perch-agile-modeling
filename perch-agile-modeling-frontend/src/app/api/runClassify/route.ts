import { NextResponse } from "next/server"

const batchLib = require("@google-cloud/batch")

export function POST(request: Request) {
    const batch = batchLib.protos.google.cloud.batch.v1

    const projectId = "caples"
    const jobName = Date.now().toString()
    const region = "us-central1"

    // Instantiates a client
    const batchClient = new batchLib.v1.BatchServiceClient()

    // Define what will be done as part of the job.
    const task = new batch.TaskSpec()
    const runnable = new batch.Runnable()
    runnable.script = new batch.Runnable.Script()
    runnable.script.text =
        "echo Hello world! This is task ${BATCH_TASK_INDEX}. This job has a total of ${BATCH_TASK_COUNT} tasks."
    // You can also run a script from a file. Just remember, that needs to be a script that's
    // already on the VM that will be running the job. Using runnable.script.text and runnable.script.path is mutually
    // exclusive.
    // runnable.script.path = '/tmp/test.sh'
    task.runnables = [runnable]

    // We can specify what resources are requested by each task.
    const resources = new batch.ComputeResource()
    resources.cpuMilli = 2000 // in milliseconds per cpu-second. This means the task requires 2 whole CPUs.
    resources.memoryMib = 16
    task.computeResource = resources

    task.maxRetryCount = 2
    task.maxRunDuration = { seconds: 3600 }

    // Tasks are grouped inside a job using TaskGroups.
    const group = new batch.TaskGroup()
    group.taskCount = 4
    group.taskSpec = task

    // Policies are used to define on what kind of virtual machines the tasks will run on.
    // In this case, we tell the system to use "e2-standard-4" machine type.
    // Read more about machine types here: https://cloud.google.com/compute/docs/machine-types
    const allocationPolicy = new batch.AllocationPolicy()
    const policy = new batch.AllocationPolicy.InstancePolicy()
    policy.machineType = "e2-standard-2"
    const instances = new batch.AllocationPolicy.InstancePolicyOrTemplate()
    instances.policy = policy
    allocationPolicy.instances = [instances]

    const job = new batch.Job()
    job.name = jobName
    job.taskGroups = [group]
    job.allocationPolicy = allocationPolicy
    job.labels = { env: "testing", type: "script" }
    // We use Cloud Logging as it's an option available out of the box
    job.logsPolicy = new batch.LogsPolicy()
    job.logsPolicy.destination = batch.LogsPolicy.Destination.CLOUD_LOGGING

    // The job's parent is the project and region in which the job will run
    const parentJob = `projects/${projectId}/locations/${region}`

    async function callCreateJob() {
        // Construct request
        const request = {
            parent: parentJob,
            jobId: jobName,
            job,
        }

        // Run request
        const response = await batchClient.createJob(request)
        console.log(response)
    }

    callCreateJob()
    return NextResponse.json({ success: true })
}
