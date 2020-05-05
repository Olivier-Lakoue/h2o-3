package water.data.transformations;

import water.DKV;
import water.Key;
import water.Scope;
import water.fvec.Frame;
import water.fvec.Vec;
import water.rapids.Merge;
import water.util.ArrayUtils;
import water.util.FrameUtils;

import java.util.Arrays;

/**
 *
 */
public class DropDuplicateRows {

    private static final String LABEL_COLUMN_NAME = "label";

    final Frame sourceFrame;
    final int[] comparedColumnIndices;
    final DropOrder dropOrder;

    public DropDuplicateRows(final Frame sourceFrame, final int[] comparedColumnIndices, final DropOrder dropOrder) {
        this.sourceFrame = sourceFrame;
        this.comparedColumnIndices = comparedColumnIndices;
        this.dropOrder = dropOrder;
    }

    public Frame dropDuplicates() {
        try {
            Scope.enter();
            FrameUtils.labelRows(sourceFrame, LABEL_COLUMN_NAME);
            final Frame sortedFrame = Scope.track(sortByComparedColumns());
            final Frame chunkBoundaries = Scope.track(new CollectChunkBorderValuesTask()
                    .doAll(sortedFrame.types(), sortedFrame)
                    .outputFrame());

            final Frame deDuplicatedFrame = Scope.track(new DropDuplicateRowsTask(chunkBoundaries, comparedColumnIndices)
                    .doAll(sortedFrame.types(), sortedFrame)
                    .outputFrame());

            final Frame outputFrame = Merge.sort(deDuplicatedFrame, deDuplicatedFrame.numCols() - 1);
            outputFrame.remove(outputFrame.numCols() - 1);
            outputFrame._key = Key.make(sourceFrame._key.toString() + "_deduplicated");
            DKV.put(outputFrame);
            return outputFrame;

        } finally {
            final Vec label = sourceFrame.remove(LABEL_COLUMN_NAME);
            if (label != null) {
                label.remove();
            }
            Scope.exit();
        }
    }


    /**
     * Creates a copy of the original dataset, sorted by all compared columns.
     * The sort is done with respect to {@link DropOrder} value.
     *
     * @return A new Frame sorted by all compared columns.
     */
    private Frame sortByComparedColumns() {
        final int labelColumnIndex = sourceFrame.find(LABEL_COLUMN_NAME);
        final int[] sortByColumns = ArrayUtils.append(comparedColumnIndices, labelColumnIndex);
        final boolean ascendingSort = DropOrder.DropFirst == dropOrder ? true : false;

        final int[] sortOrder = new int[sortByColumns.length];
        // Compared columns are always sorted in the same order
        Arrays.fill(sortOrder, 0, sortOrder.length - 1, Merge.ASCENDING);
        // Label column is sorted differently based on DropOrder
        sortOrder[sortOrder.length - 1] = ascendingSort ? Merge.ASCENDING : Merge.DESCENDING;

        return Merge.sort(sourceFrame, sortByColumns, sortOrder);
    }
}
