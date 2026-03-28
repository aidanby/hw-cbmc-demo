// 2-bit saturating counter branch predictor with 4-entry pattern table.
//
// Prediction: index table with pc[3:2], read counter, predict taken if >= 2.
// Update: after branch resolves, increment counter if taken, decrement if not.
//   Counter saturates at 0 and 3 (never wraps).
//
// Pipeline: prediction is registered (available 1 cycle after pc presented).
//   Update writes back to the table 1 cycle after resolve signals arrive.
//
// Interface:
//   predict side: pc_in → predict_taken (1 cycle later)
//   update side:  update_en + update_pc + was_taken → counter updated next cycle
//
// The predict and update paths share the pattern table, creating a
// read-write interaction when both access the same entry.
//
// Three bugs corrupt the table indexing, the prediction threshold,
// and the counter update direction.
module branch_pred(
  input        clk,
  input        reset,
  // Predict side
  input  [7:0] pc_in,
  output reg   predict_taken,
  // Update side
  input        update_en,
  input  [7:0] update_pc,
  input        was_taken
);
  // 4-entry table of 2-bit saturating counters
  reg [1:0] table [0:3];

  // Pipeline registers for prediction
  reg [1:0] pred_index;
  reg [1:0] pred_counter;

  // Pipeline registers for update
  reg       upd_en_s1;
  reg [1:0] upd_index_s1;
  reg       upd_taken_s1;
  reg [1:0] upd_counter_s1;

  // Address decomposition
  wire [1:0] pc_index     = pc_in[3:2];
  wire [1:0] update_index = update_pc[3:2];

  initial begin
    predict_taken = 0;
    pred_index = 0; pred_counter = 0;
    upd_en_s1 = 0; upd_index_s1 = 0; upd_taken_s1 = 0; upd_counter_s1 = 0;
    table[0] = 2'd1; table[1] = 2'd1; table[2] = 2'd1; table[3] = 2'd1;
  end

  always @(posedge clk) begin
    if (reset) begin
      predict_taken <= 0;
      pred_index <= 0; pred_counter <= 0;
      upd_en_s1 <= 0; upd_index_s1 <= 0; upd_taken_s1 <= 0; upd_counter_s1 <= 0;
      table[0] <= 2'd1; table[1] <= 2'd1; table[2] <= 2'd1; table[3] <= 2'd1;
    end else begin
      // ── PREDICT PIPELINE (Stage 1: read table, Stage 2: threshold) ──
      pred_index   <= pc_index;
      pred_counter <= table[pred_index]; // HINT: check this line carefully
      predict_taken <= (pred_counter >= 2'd0);

      // ── UPDATE PIPELINE (Stage 1: latch resolve, Stage 2: write back) ──
      upd_en_s1      <= update_en;
      upd_index_s1   <= update_index;
      upd_taken_s1   <= was_taken;
      upd_counter_s1 <= table[update_index];

      // Stage 2: compute new counter and write back
      if (upd_en_s1) begin
        if (upd_taken_s1) begin
          // Branch was taken: increment (saturate at 3)
          if (upd_counter_s1 < 2'd3)
            table[upd_index_s1] <= upd_counter_s1 - 2'd1; // HINT: check this line carefully
        end else begin
          // Branch was not taken: decrement (saturate at 0)
          if (upd_counter_s1 > 2'd0)
            table[upd_index_s1] <= upd_counter_s1 - 2'd1;
        end
      end
    end
  end

  // Properties
  p_reset:      assert property (@(posedge clk) reset |=> !predict_taken);
  p_pred_read:  assert property (@(posedge clk) !reset |=> pred_counter == $past(table[$past(pc_index)]));
  p_threshold:  assert property (@(posedge clk) !reset && pred_counter >= 2'd2 |-> predict_taken);
  p_not_taken:  assert property (@(posedge clk) !reset && pred_counter < 2'd2 |-> !predict_taken);
  p_inc_taken:  assert property (@(posedge clk) !reset && upd_en_s1 && upd_taken_s1 && upd_counter_s1 < 2'd3 |=> table[$past(upd_index_s1)] == ($past(upd_counter_s1) + 2'd1));
  p_dec_ntaken: assert property (@(posedge clk) !reset && upd_en_s1 && !upd_taken_s1 && upd_counter_s1 > 2'd0 |=> table[$past(upd_index_s1)] == ($past(upd_counter_s1) - 2'd1));
  p_saturate3:  assert property (@(posedge clk) !reset |=> table[0] <= 2'd3 && table[1] <= 2'd3 && table[2] <= 2'd3 && table[3] <= 2'd3);
endmodule
