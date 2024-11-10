// Copyright (c) 2003-2009 Massachusetts Institute of Technology
// Copyright (c) 2009-2015 Broad Institute
// All rights reserved.
//
// Copyright (c) 2014 Adam Karpierz
// SPDX-License-Identifier: BSD-3-Clause

package org.cellprofiler.runnablequeue;

import java.util.concurrent.Callable;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.Executor;
import java.util.concurrent.FutureTask;
import java.util.concurrent.Semaphore;
import java.util.concurrent.SynchronousQueue;

/**
 * @author Leek
 *
 * This class is solely designed to operate a single instance
 * on the main thread to allow other threads to run runnables
 * on that thread.
 *
 * Use something like FutureTask<V> if you need to return a
 * result or synchronize to the completion of the submitted
 * runnable.
 */
public class RunnableQueue implements Runnable
{
    private static SynchronousQueue<Runnable> queue = new SynchronousQueue<Runnable>();

    /* (non-Javadoc)
     * @see java.lang.Runnable#run()
     */
    @Override  // <AK> added
    public void run()
    {
        try
        {
            while ( true )
            {
                Runnable task = queue.take();
                task.run();
            }
        }
        catch ( InterruptedException exc )
        {
            // System.out.println("Exiting RunnableQueue.");
        }
    }

    /**
     * Enqueue a runnable to be executed on the thread.
     *
     * Put the runnable on the main thread's queue and return
     * asynchronous to the runnable's execution.
     *
     * @param runnable - run this runnable.
     * @throws InterruptedException on thread interruption
     */
    static public void enqueue(Runnable runnable) throws InterruptedException
    {
        queue.put(new FutureTask<Object>(runnable, null));
    }

    /**
     * Execute a runnable synchronously.
     *
     * @param runnable - runnable to be executed
     * @throws InterruptedException if thread was interrupted while enqueueing runnable
     * @throws ExecutionException if there was an exception while running the runnable
     */
    static public void execute(Runnable runnable) throws InterruptedException, ExecutionException
    {
        FutureTask<Object> future = new FutureTask<Object>(runnable, null);
        enqueue(future);
        future.get();
    }

    /**
     * Execute a callable synchronously returning the callable's result.
     *
     * @param <V> the type of result to be returned
     * @param callable the callable to be executed on the main thread
     * @return the result of the callable's execution
     *
     * @throws InterruptedException
     * @throws ExecutionException
     */
    static public <V> V execute(Callable<V> callable) throws InterruptedException, ExecutionException
    {
        FutureTask<V> future = new FutureTask<V>(callable);
        enqueue(future);
        return future.get();
    }

    /**
     * Stop the main thread.
     *
     * @throws InterruptedException if this thread was waiting for initialization and was interrupted.
     * @throws ExecutionException
     */
    static public void stop() throws InterruptedException, ExecutionException
    {
        Runnable r = new Runnable() {
            @Override  // <AK> added
            public void run()
            {
                Thread.currentThread().interrupt();
            }
        };
        execute(r);
    }
}
